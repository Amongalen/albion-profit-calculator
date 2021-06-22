import logging
import shutil

import requests

from albion_calculator import items

URL = 'https://render.albiononline.com/v1/item/{item_id}.png'
ICON_FILENAME = 'resources/icons/{item_id}.png'


def download_icon(item_id):
    url = URL.format(item_id=item_id)
    response = requests.get(url, stream=True, params={'size': 100})
    if not response.ok:
        logging.error(f'{response.status_code} {response.text}')
        return
    response.raw.decode_content = True
    filename = ICON_FILENAME.format(item_id=item_id)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)


if __name__ == '__main__':
    item_ids = items.get_all_items_ids()
    for item_id in item_ids:
        download_icon(item_id)
