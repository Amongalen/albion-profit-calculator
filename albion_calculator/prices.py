import functools
import json
import pathlib
from collections import defaultdict
from datetime import datetime, timedelta
from math import nan

import numpy as np
import requests as requests

from albion_calculator.cities import cities_names

CACHE_LIFETIME = 12

CACHE_FILENAME = '../cache/price.cache'

API_ADDRESS = 'https://www.albion-online-data.com/api/v2/stats/{type}/{items}.json'

REQUEST_PARAMS = {'locations': ','.join(cities_names()),
                  'time-scale': 6,
                  'qualities': '1,2,3,4'}

CHUNK_SIZE = 2

DEVIATION_THRESHOLD = 2


def local_price_cache(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = read_local_cache_file()
        if result is None:
            result = func(*args, **kwargs)
            write_to_local_cache_file(result)
        return result

    return wrapper


@local_price_cache
def load_all_prices(items_ids):
    prices = {}
    for chunk in chunks(items_ids, CHUNK_SIZE):
        prices.update(get_prices_data_for_chunk(chunk))
    return prices


def merge_quality_data(history_prices):
    prices_with_merged_qualities = defaultdict(dict)
    for item_id, prices_for_item in history_prices.items():
        for city_name, prices_in_city in prices_for_item.items():
            result_price_in_city = prices_in_city[0]
            for record in prices_in_city[1:]:
                result_price_in_city['data'].extend(record['data'])
            prices_with_merged_qualities[item_id][city_name] = result_price_in_city
    return prices_with_merged_qualities


def filter_latest_quality_data(latest_prices):
    prices_with_filtered_qualities = defaultdict(dict)
    for item_id, prices_for_item in latest_prices.items():
        for city_name, prices_in_city in prices_for_item.items():
            sorted_prices = sorted(prices_in_city, key=lambda x: x['sell_price_min_date'], reverse=True)
            prices_with_filtered_qualities[item_id][city_name] = sorted_prices[0]
    return prices_with_filtered_qualities


def get_prices_data_for_chunk(items_ids):
    history_prices, latest_prices = get_prices_from_api(items_ids)

    history_prices_by_item = group_by_attr(history_prices, 'item_id')
    latest_prices_by_item = group_by_attr(latest_prices, 'item_id')

    history_prices_by_item_and_city = {k: group_by_attr(v, 'location') for k, v in history_prices_by_item.items()}
    latest_prices_by_item_and_city = {k: group_by_attr(v, 'city') for k, v in latest_prices_by_item.items()}
    history_prices_with_merged_quality = merge_quality_data(history_prices_by_item_and_city)
    filtered_latest_prices = filter_latest_quality_data(latest_prices_by_item_and_city)
    result = {}
    for item_id in items_ids:
        history_prices_for_item = history_prices_with_merged_quality.get(item_id, {})
        latest_prices_for_item = filtered_latest_prices.get(item_id, {})
        result[item_id] = merge_latest_and_history_prices(history_prices_for_item, latest_prices_for_item)
    return result


def merge_latest_and_history_prices(history_prices_for_item, latest_prices_for_item):
    merged_prices_by_city = []
    for city in cities_names():
        history_price = history_prices_for_item.get(city, {})
        history_price_summary = summarize_history_price(history_price)
        latest_price = normalize_datetime_format(latest_prices_for_item.get(city, {}))
        merged_prices_by_city.append(history_price_summary | latest_price)
    return merged_prices_by_city


def group_by_attr(elements, attr):
    result = defaultdict(list)
    for record in elements:
        item_id = record[attr]
        result[item_id].append(record)
    return result


def get_prices_from_api(items_ids):
    items_parameter = ','.join(items_ids)
    history_url = API_ADDRESS.format(type='history', items=items_parameter)
    prices_url = API_ADDRESS.format(type='prices', items=items_parameter)
    history_prices = get_json_from_url(history_url)
    latest_prices = get_json_from_url(prices_url)
    return history_prices, latest_prices


def get_prices_for_item(item_id):
    result = []
    prices = items_prices.get(item_id, None)
    if prices is None:
        a = np.empty((6,))
        a[:] = nan
        return a
    for record in prices:
        if not record:
            result.append(nan)
            continue
        min_price = record['sell_price_min']
        avg_price_24h = record.get('avg_price_24h', 0)
        # deviation used to remove anomalous values
        deviation = min_price / avg_price_24h if avg_price_24h != 0 else min_price
        if min_price != 0 and 1 / DEVIATION_THRESHOLD <= deviation <= DEVIATION_THRESHOLD:
            price = min_price
        elif avg_price_24h != 0:
            price = avg_price_24h
        else:
            price = nan
        result.append(price)
    return np.array(result)


def get_price_for_item_in_city(item_id, city_index):
    return get_prices_for_item(item_id)[city_index]


def get_avg_price_for_item(item_id):
    return np.nanmean(get_prices_for_item(item_id))


def summarize_history_price(history_price):
    if not history_price:
        return {}
    data = sorted(history_price['data'], key=lambda x: x['timestamp'], reverse=True)
    latest_record = data[0]
    latest_timestamp = parse_timestamp(latest_record['timestamp'])
    previous_day = latest_timestamp - timedelta(days=1)
    items_sold = sum(record['item_count'] for record in data)

    data_24h = [record for record in data if parse_timestamp(record['timestamp']) > previous_day]
    price_sum_24h = sum(record['avg_price'] * record['item_count'] for record in data_24h)
    items_sold_24h = sum(record['item_count'] for record in data_24h)
    avg_price_24h = round(price_sum_24h / items_sold_24h, 3)

    summary = {'item_id': history_price['item_id'],
               'latest_timestamp': str(latest_timestamp),
               'items_sold': items_sold,
               'avg_price_24h': avg_price_24h}

    return summary


def parse_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')


def get_json_from_url(url):
    response = requests.get(url, params=REQUEST_PARAMS)
    if not response:
        response_json = None
    else:
        response_json = response.json()
    return response_json


def read_local_cache_file():
    if not is_cache_up_to_date():
        return None
    with open(CACHE_FILENAME) as f:
        cache = json.load(f)
    return cache


def write_to_local_cache_file(cache_json):
    with open(CACHE_FILENAME, 'w') as f:
        json.dump(cache_json, f, indent=1)


def is_cache_up_to_date():
    file_metadata = pathlib.Path(CACHE_FILENAME)

    if not file_metadata.exists():
        return False

    modification_time = datetime.fromtimestamp(file_metadata.stat().st_mtime)
    current_time = datetime.now()
    elapsed_time = current_time - modification_time
    hours_passed = elapsed_time // timedelta(hours=1)
    if hours_passed >= CACHE_LIFETIME:
        return False

    return True


def normalize_datetime_format(record):
    record['sell_price_min_date'] = str(parse_timestamp(record['sell_price_min_date']))
    record['sell_price_max_date'] = str(parse_timestamp(record['sell_price_max_date']))
    record['buy_price_min_date'] = str(parse_timestamp(record['buy_price_min_date']))
    record['buy_price_max_date'] = str(parse_timestamp(record['buy_price_max_date']))
    return record


def chunks(lst, n):
    # Yield successive n-sized chunks from lst.
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# items_ids = items.load_items().keys()

# for testing
items_ids = ['T5_MAIN_SWORD', 'T5_PLANKS', 'T5_METALBAR', 'T5_LEATHER', 'T5_JOURNAL_WARRIOR_FULL']

items_prices = load_all_prices(items_ids)
