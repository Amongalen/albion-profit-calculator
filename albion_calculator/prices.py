import functools
import json
import pathlib
from datetime import datetime, timedelta

import requests as requests

from albion_calculator import items

CACHE_LIFETIME = 12

CACHE_FILENAME = '../cache/price.cache'

API_ADDRESS = 'https://www.albion-online-data.com/api/v2/stats/{type}/{items}.json'

CITIES = ['Bridgewatch', 'Fort Sterling', 'Caerleon', 'Martlock', 'Thetford', 'Lymhurst']
REQUEST_PARAMS = {'locations': ','.join(CITIES),
                  'time-scale': 1,
                  'qualities': 1}


def local_price_cache(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = load_local_cache()
        if result is None:
            result = func(*args, **kwargs)
            write_to_local_cache(result)
        return result

    return wrapper


@local_price_cache
def get_all_prices(items):
    all_prices = {}
    for item in items:
        prices = get_prices_for_one_item(item)
        all_prices[item] = prices
    return all_prices


def get_prices_for_one_item(item):
    history_url = API_ADDRESS.format(type='history', items=item)
    prices_url = API_ADDRESS.format(type='prices', items=item)

    history_prices = get_json_from_url(history_url)
    latest_prices = get_json_from_url(prices_url)
    history_prices_by_city = {record['location']: record for record in history_prices}
    latest_prices_by_city = {record['city']: record for record in latest_prices}
    merged_prices_by_city = {}
    for city in CITIES:
        history_price = history_prices_by_city.get(city, {})
        history_price_summary = summarize_history_price(history_price)
        latest_price = latest_prices_by_city.get(city, {})
        merged_prices_by_city[city] = history_price_summary | latest_price
    return merged_prices_by_city


def summarize_history_price(history_price):
    summary = {}
    return summary


def get_json_from_url(url):
    response = requests.get(url, params=REQUEST_PARAMS)
    if not response:
        response_json = None
    else:
        response_json = response.json()
    return response_json


def load_local_cache():
    if not is_cache_up_to_date():
        return None
    with open(CACHE_FILENAME) as f:
        cache = json.load(f)
    return cache


def write_to_local_cache(cache_json):
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


if __name__ == '__main__':
    # items = items.load_items()
    # items_ids = items.keys()

    items_ids = ['T5_WOOD', 'T5_PLANKS', 'T5_BAG', 'T4_POTION_HEAL']
    result = get_all_prices(items_ids)
    print(result)
