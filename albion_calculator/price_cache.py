import functools
import json
import pathlib
from datetime import datetime, timedelta
from typing import Optional


def local_price_cache(func: callable) -> callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = _read_local_cache_file()
        if result is None:
            result = func(*args, **kwargs)
            _write_to_local_cache_file(result)
        return result

    return wrapper


def _read_local_cache_file() -> Optional[dict]:
    if not _is_cache_up_to_date():
        return None
    with open(_CACHE_FILENAME) as f:
        cache = json.load(f)
    return cache


def _write_to_local_cache_file(cache_json: dict) -> None:
    with open(_CACHE_FILENAME, 'w') as f:
        json.dump(cache_json, f, indent=1)


def _is_cache_up_to_date() -> bool:
    file_metadata = pathlib.Path(_CACHE_FILENAME)

    if not file_metadata.exists():
        return False

    modification_time = datetime.fromtimestamp(file_metadata.stat().st_mtime)
    current_time = datetime.now()
    elapsed_time = current_time - modification_time
    hours_passed = elapsed_time // timedelta(hours=1)
    return hours_passed < _CACHE_LIFETIME


_CACHE_LIFETIME = 6
_CACHE_FILENAME = 'cache/price.cache'
