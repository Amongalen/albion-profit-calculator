import logging

import requests as requests

from albion_calculator import config

_API_ADDRESS = config.CONFIG['DATA_PROJECT']['API_ADDRESS'] + '/{type}/{items}.json'
_REQUEST_PARAMS = config.get_api_params()


def get_prices(items_ids: list[str]) -> tuple[list, list]:
    items_parameter = ','.join(items_ids)
    history_url = _API_ADDRESS.format(type='history', items=items_parameter)
    prices_url = _API_ADDRESS.format(type='prices', items=items_parameter)
    history_prices = _get_json_from_url(history_url)
    latest_prices = _get_json_from_url(prices_url)
    return history_prices, latest_prices


def _get_json_from_url(url: str) -> list[dict]:
    response = requests.get(url, params=_REQUEST_PARAMS)
    if not response.ok:
        logging.error(f'{response.status_code} {response.text}')
    return response.json() if response.ok else None
