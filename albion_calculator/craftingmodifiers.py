import json

import numpy as np
from numpy import ndarray

from albion_calculator import items
from albion_calculator.cities import cities_names

_SUBCATEGORY_REPLACEMENTS = {'ore': 'metalbar',
                             'wood': 'planks',
                             'hide': 'leather',
                             'fiber': 'cloth',
                             'rock': 'stoneblock'}
_CLUSTER_ID = {'0000': 'Thetford', '1000': 'Lymhurst', '2000': 'Bridgewatch',
               '3004': 'Martlock', '4000': 'Fort Sterling', '3003': 'Caerleon'}

_BASE_CRAFTING_BONUS = 0.18


def get_craftable_categories() -> list[str]:
    return [subcategory for city in _crafting_bonus.values() for subcategory in city.keys()]


def get_return_rates_vector(item_id: str, use_focus: bool = False) -> ndarray:
    item_subcategory = items.get_item_subcategory(item_id)
    vector = [_get_return_rate(city, item_subcategory, use_focus) for city in cities_names()]
    return np.atleast_2d(1 - np.array(vector)).T


def _load_crafting_modifiers() -> dict[str, dict[str, float]]:
    raw_data = _load_crafting_modifiers_file()
    crafting_modifiers = {}
    for location in raw_data:
        city_id = _CLUSTER_ID.get(location.get('@clusterid', None), None)
        if city_id is None:
            continue
        crafting_modifiers[city_id] = {_replace_refining_category(modifier['@name']): float(modifier['@value'])
                                       for modifier in location['craftingmodifier']}
    return crafting_modifiers


def _get_return_rate(city_id: str, item_category: str, use_focus: bool = False) -> float:
    focus_bonus = 0.59 if use_focus else 0
    local_crafting_bonus = _crafting_bonus[city_id].get(item_category, 0) + _BASE_CRAFTING_BONUS + focus_bonus
    return round(1 - 1 / (1 + local_crafting_bonus), 3)


def _replace_refining_category(name: str) -> str:
    return _SUBCATEGORY_REPLACEMENTS.get(name, name)


def _load_crafting_modifiers_file() -> list[dict]:
    with open('resources/craftingmodifiers.json') as f:
        raw_crafting_modifiers_data = json.load(f)
    return raw_crafting_modifiers_data['craftingmodifiers']['craftinglocation']


_crafting_bonus = _load_crafting_modifiers()
