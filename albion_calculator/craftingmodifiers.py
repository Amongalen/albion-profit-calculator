import json

import numpy as np

from albion_calculator import items
from albion_calculator.cities import cities_names

SUBCATEGORY_REPLACEMENTS = {'ore': 'metalbar',
                            'wood': 'planks',
                            'hide': 'leather',
                            'fiber': 'cloth',
                            'rock': 'stoneblock'}
CLUSTER_ID = {'0000': 'Thetford', '1000': 'Lymhurst', '2000': 'Bridgewatch',
              '3004': 'Martlock', '4000': 'Fort Sterling', '3003': 'Caerleon'}

BASE_CRAFTING_BONUS = 0.18


def load_crafting_modifiers():
    raw_data = load_crafting_modifiers_file()
    crafting_modifiers = {}
    for location in raw_data:
        city = CLUSTER_ID.get(location.get('@clusterid', None), None)
        if city is None:
            continue
        crafting_modifiers[city] = {replace_refining_category(modifier['@name']): float(modifier['@value'])
                                    for modifier in location['craftingmodifier']}
    return crafting_modifiers


def get_return_rates_vector(item_id, use_focus=False):
    item_subcategory = items.get_item_subcategory(item_id)
    vector = [get_return_rate(city, item_subcategory, use_focus) for city in cities_names()]
    return np.atleast_2d(1 - np.array(vector)).T


def get_return_rate(city, item_category, use_focus=False):
    focus_bonus = 0.59 if use_focus else 0
    local_crafting_bonus = crafting_bonus[city].get(item_category, 0) + BASE_CRAFTING_BONUS + focus_bonus
    return round(1 - 1 / (1 + local_crafting_bonus), 3)


def replace_refining_category(name):
    return SUBCATEGORY_REPLACEMENTS.get(name, name)


def load_crafting_modifiers_file():
    with open('resources/craftingmodifiers.json') as f:
        raw_crafting_modifiers_data = json.load(f)
    return raw_crafting_modifiers_data['craftingmodifiers']['craftinglocation']


def get_craftable_categories():
    return [subcategory for city in crafting_bonus.values() for subcategory in city.keys()]


crafting_bonus = load_crafting_modifiers()
subcategories = get_craftable_categories()
