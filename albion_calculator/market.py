import functools
import json
import logging
import pathlib
from collections import defaultdict
from datetime import datetime, timedelta
from math import nan

import numpy as np
import requests as requests
import tqdm as tqdm

from albion_calculator import items, config
from albion_calculator.cities import cities_names

CACHE_LIFETIME = 11

CACHE_FILENAME = 'cache/price.cache'

API_ADDRESS = config.CONFIG['DATA_PROJECT']['API_ADDRESS'] + '/{type}/{items}.json'

DOWNLOAD_CHUNK_SIZE = config.CONFIG['DATA_PROJECT']['DOWNLOAD_CHUNK_SIZE']

REQUEST_PARAMS = config.get_api_params()

DEVIATION_THRESHOLD = 4

items_prices = {}

estimated_real_prices = {}


def get_price_for_item_in_city(item_id, city_index):
    return get_prices_for_item(item_id)[city_index]


def get_prices_for_item(item_id):
    prices = estimated_real_prices.get(item_id, None)
    if prices is None:
        a = np.empty((6,))
        a[:] = nan
        return a

    return prices


def estimate_real_prices_for_item(item_id):
    return np.array([estimate_real_price(prices_in_city) for prices_in_city in items_prices[item_id]])


def estimate_real_price(prices_in_city):
    if not prices_in_city:
        return nan

    min_price = prices_in_city.get('sell_price_min', 0)
    avg_price_24h = prices_in_city.get('avg_price_24h', 0)

    if avg_price_24h == 0:
        return nan

    # deviation used to remove anomalous values
    deviation = min_price / avg_price_24h
    if min_price != 0 and 1 / DEVIATION_THRESHOLD <= deviation <= DEVIATION_THRESHOLD:
        return min_price
    return avg_price_24h


def get_avg_price_for_item(item_id):
    return np.nanmean(get_prices_for_item(item_id))


def get_amount_sold(item_id, city):
    return items_prices[item_id][city].get('items_sold', 0)


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
    return {k: v for chunk in chunks(items_ids, DOWNLOAD_CHUNK_SIZE)
            for k, v in get_prices_data_for_chunk(chunk).items()}


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

    if history_prices is None or latest_prices is None:
        return {}

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


def summarize_history_price(history_price):
    if not history_price:
        return {}
    data = sorted(history_price['data'], key=lambda x: x['timestamp'], reverse=True)
    latest_timestamp = parse_timestamp(data[0]['timestamp'])
    day_before = latest_timestamp - timedelta(days=1)

    data_24h = [record for record in data if parse_timestamp(record['timestamp']) > day_before]
    price_sum_24h = sum(record['avg_price'] * record['item_count'] for record in data_24h)
    items_sold_count_24h = sum(record['item_count'] for record in data_24h)
    avg_price_24h = round(price_sum_24h / items_sold_count_24h, 3) if items_sold_count_24h > 0 else 0

    items_sold = sum(record['item_count'] for record in data)
    return {'item_id': history_price['item_id'],
            'latest_timestamp': str(latest_timestamp),
            'items_sold': items_sold,
            'avg_price_24h': avg_price_24h}


def parse_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')


def get_json_from_url(url):
    response = requests.get(url, params=REQUEST_PARAMS)
    if not response.ok:
        logging.error(f'{response.status_code} {response.text}')
    return response.json() if response.ok else None


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
    return hours_passed < CACHE_LIFETIME


def normalize_datetime_format(record):
    record['sell_price_min_date'] = str(parse_timestamp(record['sell_price_min_date']))
    record['sell_price_max_date'] = str(parse_timestamp(record['sell_price_max_date']))
    record['buy_price_min_date'] = str(parse_timestamp(record['buy_price_min_date']))
    record['buy_price_max_date'] = str(parse_timestamp(record['buy_price_max_date']))
    return record


def chunks(lst, n):
    # Yield successive n-sized chunks from lst.
    for i in tqdm.tqdm(range(0, len(lst), n), desc='Pulling prices'):
        yield lst[i:i + n]


def correct_erroneous_prices(estimated_prices):
    corrected_prices = {}
    for item_id, prices_for_item in estimated_prices.items():
        sorted_prices = sorted(prices_for_item)
        _, q3 = np.nanpercentile(sorted_prices, [25, 75], interpolation='lower')
        q1, _ = np.nanpercentile(sorted_prices, [25, 75], interpolation='higher')
        iqr = q3 - q1 if not q3 == q1 else 50  # a nice magic number
        lower_bound = q1 - (1.3 * iqr)
        upper_bound = q3 + (1.3 * iqr)
        corrected_prices_for_item = []
        for price in prices_for_item:
            corrected_price = price if lower_bound <= price <= upper_bound else nan
            corrected_prices_for_item.append(corrected_price)
        corrected_prices[item_id] = np.array(corrected_prices_for_item)
    return corrected_prices


def update_prices():
    global items_prices, estimated_real_prices
    items_ids = items.get_all_items_ids()
    items_prices = load_all_prices(items_ids)
    estimated_prices = {item_id: estimate_real_prices_for_item(item_id) for item_id in items_ids}
    estimated_real_prices = correct_erroneous_prices(estimated_prices)
