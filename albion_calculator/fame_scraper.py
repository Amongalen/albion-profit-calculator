import json

import requests
from bs4 import BeautifulSoup

from albion_calculator import items, craftingmodifiers

URL = 'https://www.albiononline2d.com/en/item/id/'


# item_ids for enchanted refined resources are wrong so no fame for those but we don't care about them anyway
# only needed for crafting items with journals

def convert_text_to_int(amount_text):
    if 'k' in amount_text.lower():
        return float(amount_text[:-1]) * 1000
    return int(amount_text)


def get_fame_for_item(item_id):
    page = requests.get(URL + item_id)
    if not page:
        return None
    soup = BeautifulSoup(page.content, 'html.parser')
    cell_with_fame_label = soup.findAll('td', text='Crafting Fame (Premium)')
    if not cell_with_fame_label:
        return None
    row = cell_with_fame_label[0].parent
    amount_text = row.contents[1].text
    fame_with_premium = convert_text_to_int(amount_text)
    fame_no_premium = fame_with_premium / 1.5
    return int(fame_no_premium)


def get_crafting_fame_for_items(*args):
    return {item_id: get_fame_for_item(item_id) for item_id in args}


def save_crafting_fame_to_file(content_dict):
    with open(items.CRAFTING_FAME_JSON_FILE, 'w+') as f:
        json.dump(content_dict, f)


if __name__ == '__main__':
    craftable_subcategories = craftingmodifiers.get_craftable_categories()
    items_ids = items.get_items_ids_for_category_or_subcategory(*craftable_subcategories)
    crafting_fame_dict = get_crafting_fame_for_items(*items_ids, 'accessories')
    save_crafting_fame_to_file(crafting_fame_dict)
