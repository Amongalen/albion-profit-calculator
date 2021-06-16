from collections import defaultdict
from datetime import datetime, timedelta
from math import nan

import numpy as np
import tqdm as tqdm

from albion_calculator import items, config
from albion_calculator.cities import cities_names
from albion_calculator.price_api import get_prices
from albion_calculator.price_cache import local_price_cache

_DOWNLOAD_CHUNK_SIZE = config.CONFIG['DATA_PROJECT']['DOWNLOAD_CHUNK_SIZE']

_DEVIATION_THRESHOLD = 4

_items_prices = {}

_estimated_real_prices = {}


def get_price_for_item_in_city(item_id, city_index):
    return get_prices_for_item(item_id)[city_index]


def get_prices_for_item(item_id):
    prices = _estimated_real_prices.get(item_id, None)
    if prices is None:
        a = np.empty((6,))
        a[:] = nan
        return a

    return prices


def _estimate_real_prices_for_item(item_id):
    return np.array([_estimate_real_price(prices_in_city) for prices_in_city in _items_prices[item_id]])


def _estimate_real_price(prices_in_city):
    if not prices_in_city:
        return nan

    min_price = prices_in_city.get('sell_price_min', 0)
    avg_price_24h = prices_in_city.get('avg_price_24h', 0)

    if avg_price_24h == 0:
        return nan

    # deviation used to remove anomalous values
    deviation = min_price / avg_price_24h
    if min_price != 0 and 1 / _DEVIATION_THRESHOLD <= deviation <= _DEVIATION_THRESHOLD:
        return min_price
    return avg_price_24h


def get_avg_price_for_item(item_id):
    return np.nanmean(get_prices_for_item(item_id))


@local_price_cache
def _load_all_prices(items_ids):
    return {k: v for chunk in _chunks(items_ids, _DOWNLOAD_CHUNK_SIZE)
            for k, v in _get_prices_data_for_chunk(chunk).items()}


def _merge_quality_data(history_prices):
    prices_with_merged_qualities = defaultdict(dict)
    for item_id, prices_for_item in history_prices.items():
        for city_name, prices_in_city in prices_for_item.items():
            result_price_in_city = prices_in_city[0]
            for record in prices_in_city[1:]:
                result_price_in_city['data'].extend(record['data'])
            prices_with_merged_qualities[item_id][city_name] = result_price_in_city
    return prices_with_merged_qualities


def _filter_latest_quality_data(latest_prices):
    prices_with_filtered_qualities = defaultdict(dict)
    for item_id, prices_for_item in latest_prices.items():
        for city_name, prices_in_city in prices_for_item.items():
            sorted_prices = sorted(prices_in_city, key=lambda x: x['sell_price_min_date'], reverse=True)
            prices_with_filtered_qualities[item_id][city_name] = sorted_prices[0]
    return prices_with_filtered_qualities


def _get_prices_data_for_chunk(items_ids):
    history_prices, latest_prices = get_prices(items_ids)

    if history_prices is None or latest_prices is None:
        return {}

    history_prices_by_item = _group_by_attr(history_prices, 'item_id')
    latest_prices_by_item = _group_by_attr(latest_prices, 'item_id')

    history_prices_by_item_and_city = {k: _group_by_attr(v, 'location') for k, v in history_prices_by_item.items()}
    latest_prices_by_item_and_city = {k: _group_by_attr(v, 'city') for k, v in latest_prices_by_item.items()}
    history_prices_with_merged_quality = _merge_quality_data(history_prices_by_item_and_city)
    filtered_latest_prices = _filter_latest_quality_data(latest_prices_by_item_and_city)
    result = {}
    for item_id in items_ids:
        history_prices_for_item = history_prices_with_merged_quality.get(item_id, {})
        latest_prices_for_item = filtered_latest_prices.get(item_id, {})
        result[item_id] = _merge_latest_and_history_prices(history_prices_for_item, latest_prices_for_item)
    return result


def _merge_latest_and_history_prices(history_prices_for_item, latest_prices_for_item):
    merged_prices_by_city = []
    for city in cities_names():
        history_price = history_prices_for_item.get(city, {})
        history_price_summary = _summarize_history_price(history_price)
        latest_price = _normalize_datetime_format(latest_prices_for_item.get(city, {}))
        merged_prices_by_city.append(history_price_summary | latest_price)
    return merged_prices_by_city


def _summarize_history_price(history_price):
    if not history_price:
        return {}
    data = sorted(history_price['data'], key=lambda x: x['timestamp'], reverse=True)
    latest_timestamp = _parse_timestamp(data[0]['timestamp'])
    day_before = latest_timestamp - timedelta(days=1)

    data_24h = [record for record in data if _parse_timestamp(record['timestamp']) > day_before]
    price_sum_24h = sum(record['avg_price'] * record['item_count'] for record in data_24h)
    items_sold_count_24h = sum(record['item_count'] for record in data_24h)
    avg_price_24h = round(price_sum_24h / items_sold_count_24h, 3) if items_sold_count_24h > 0 else 0

    items_sold = sum(record['item_count'] for record in data)
    return {'item_id': history_price['item_id'],
            'latest_timestamp': str(latest_timestamp),
            'items_sold': items_sold,
            'avg_price_24h': avg_price_24h}


def _group_by_attr(elements, attr):
    result = defaultdict(list)
    for record in elements:
        item_id = record[attr]
        result[item_id].append(record)
    return result


def _parse_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')

def _normalize_datetime_format(record):
    record['sell_price_min_date'] = str(_parse_timestamp(record['sell_price_min_date']))
    record['sell_price_max_date'] = str(_parse_timestamp(record['sell_price_max_date']))
    record['buy_price_min_date'] = str(_parse_timestamp(record['buy_price_min_date']))
    record['buy_price_max_date'] = str(_parse_timestamp(record['buy_price_max_date']))
    return record


def _chunks(lst, n):
    # Yield successive n-sized chunks from lst.
    for i in tqdm.tqdm(range(0, len(lst), n), desc='Pulling prices'):
        yield lst[i:i + n]


def _correct_erroneous_prices(estimated_prices):
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
    global _items_prices, _estimated_real_prices
    items_ids = items.get_all_items_ids()
    _items_prices = _load_all_prices(items_ids)
    estimated_prices = {item_id: _estimate_real_prices_for_item(item_id) for item_id in items_ids}
    _estimated_real_prices = _correct_erroneous_prices(estimated_prices)
