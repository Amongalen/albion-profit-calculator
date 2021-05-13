import functools
import pathlib
from datetime import datetime, timedelta

import requests as requests

from albion_calculator import items

CACHE_LIFETIME = 12

CACHE_FILENAME = '../cache/price.cache'


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


def load_local_cache():
    if not is_cache_up_to_date():
        return None
    with open(CACHE_FILENAME) as f:
        cache = f.read()
    return cache


def write_to_local_cache(cache_text):
    with open(CACHE_FILENAME, 'w') as f:
        f.write(cache_text)


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
def get_prices(items):
    return 'test5'


if __name__ == '__main__':
    items = items.load_items()
    result = get_prices(items)
    print(result)
