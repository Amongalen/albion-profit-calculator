import copy
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, NamedTuple

FILTERED_CATEGORIES = {'luxurygoods', 'other', 'token', 'trophies', 'farmables'}
FILTERED_SUBCATEGORIES = {'unique', 'vanity', 'unique_shoes', 'unique_helmet', 'unique_armor', 'repairkit', 'flag',
                          'banner', 'decoration_furniture', 'morgana_furniture', 'keeper_furniture',
                          'heretic_furniture'}
WANTED_ITEM_TYPES = ['farmableitem', 'simpleitem', 'consumableitem', 'equipmentitem',
                     'weapon', 'mount', 'furnitureitem', 'journalitem']


@dataclass
class Recipe:
    result_quantity: int = 0
    ingredients: List[NamedTuple('Ingredient', resource_id=str, quantity=int)] = field(default_factory=list)


@dataclass
class Item:
    id: str
    name: str
    category: str
    subcategory: str
    recipes: List[Recipe] = field(default_factory=list)
    item_value: int = 0


def is_item_useful(item):
    category = item['@shopcategory']
    subcategory = item['@shopsubcategory1']
    if category in FILTERED_CATEGORIES and not subcategory == 'royalsigils':
        return False
    if subcategory in FILTERED_SUBCATEGORIES:
        return False
    if category == 'furniture' and item['@uniquename'].startswith('UNIQUE'):
        return False
    return True


def remove_weird_items_without_names(items):
    return {k: v for k, v in items.items() if 'name' in v}


def create_items(raw_items_data, items_names):
    items = {}
    # there are some weird items without name, probably unused ones - lets remove those
    raw_items_data = {k: v for k, v in raw_items_data.items() if k in items_names}
    for item_id, item_data in raw_items_data.items():
        if not is_item_useful(item_data):
            continue
        name = items_names[item_id]
        category = item_data['@shopcategory']
        subcategory = item_data['@shopsubcategory1']
        item = Item(item_id, name, category, subcategory)
        items[item_id] = item

    return items


def load_items():
    raw_items_data = load_items_file()
    items_names = get_item_names()
    enchantment_items = pull_out_enchantments(raw_items_data)
    raw_items_data = raw_items_data | enchantment_items
    items = create_items(raw_items_data, items_names)
    return items


def load_items_file():
    with open('../resources/items.json') as f:
        raw_items_data = json.load(f)
        raw_items_data = raw_items_data['items']
    items = {add_missing_at_symbol(item['@uniquename']): item for item_type in WANTED_ITEM_TYPES for item in
             raw_items_data[item_type]}
    return items


def add_missing_at_symbol(name):
    special_at1_cases = ['T5_MOUNT_COUGAR_KEEPER', 'T8_MOUNT_HORSE_UNDEAD', 'T8_MOUNT_COUGAR_KEEPER',
                         'T8_MOUNT_ARMORED_HORSE_MORGANA', 'T8_MOUNT_MAMMOTH_BATTLE']
    if name in special_at1_cases:
        return name + '@1'
    match = re.search(r'(WOOD|ROCK|ORE|HIDE|FIBER|PLANKS|METALBAR|LEATHER|CLOTH)_LEVEL(\d)$', name)
    if match is None:
        return name
    return name + '@' + match.group(2)


def get_item_names():
    items_names = {}
    with open('../resources/item_names.txt') as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 3:
                item_id = parts[1].strip()
                # .split('@')[0]
                item_name = parts[2].strip()
                items_names[item_id] = item_name
    return items_names


def extract_recipes(items):
    recipes = defaultdict(list)
    for k, v in items.items():
        recipe = v.get('craftingrequirements', None)
        if recipe is not None:
            if isinstance(recipe, list):
                recipes[k].extend(recipe)
            else:
                recipes[k].append(recipe)
    return recipes


def pull_out_enchantments(raw_items_data):
    new_items = {}
    for k, v in raw_items_data.items():
        enchantments = v.get('enchantments', {}).get('enchantment', None)
        if enchantments is not None:
            if not isinstance(enchantments, list):
                enchantments = [enchantments]

            for enchantment in enchantments:
                new_item = copy.deepcopy(v)
                del new_item['craftingrequirements']
                del new_item['enchantments']
                new_item['craftingrequirements'] = enchantment['craftingrequirements']
                new_item['upgraderequirements'] = enchantment['upgraderequirements']
                new_id = new_item['@uniquename'] + '@' + enchantment['@enchantmentlevel']
                new_item['@uniquename'] = new_id
                new_items[new_id] = new_item

    return new_items


def run():
    items = load_items()

    items_by_category = defaultdict(list)
    for item in items.values():
        category = item.get('@shopcategory')
        items_by_category[category].append(item)
    items_by_subcategory = defaultdict(list)
    for item in items.values():
        subcategory = item.get('@shopsubcategory1')
        items_by_subcategory[subcategory].append(item)
    for item in items.values():
        if 'name' not in item:
            print(item['@uniquename'])

    print('end')


if __name__ == '__main__':
    run()
