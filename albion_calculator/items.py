import copy
import json
from collections import defaultdict

FILTERED_CATEGORIES = {'luxurygoods', 'other', 'token', 'trophies', 'farmables'}
FILTERED_SUBCATEGORIES = {'unique', 'vanity', 'unique_shoes', 'unique_helmet', 'unique_armor', 'repairkit', 'flag',
                          'banner', 'decoration_furniture', 'morgana_furniture', 'keeper_furniture',
                          'heretic_furniture'}
WANTED_ITEM_TYPES = ['farmableitem', 'simpleitem', 'consumableitem', 'equipmentitem',
                     'weapon', 'mount', 'furnitureitem', 'journalitem']


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


def load_items():
    with open('../resources/items.json') as f:
        raw_items_data = json.load(f)
        raw_items_data = raw_items_data['items']
    items = {item['@uniquename']: item for item_type in WANTED_ITEM_TYPES for item in raw_items_data[item_type] if
             is_item_useful(item)}
    add_item_names(items)
    items = remove_weird_items_without_names(items)
    items.update(pull_out_enchantments(items))
    return items


def add_item_names(items):
    with open('../resources/item_names.txt') as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 3:
                item_id = parts[1].strip().split('@')[0]
                item_name = parts[2].strip()
                if item_id in items:
                    item = items[item_id]
                    item['name'] = item_name


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


def pull_out_enchantments(items):
    new_items = {}
    for k, v in items.items():
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

    recipes = extract_recipes(items)

    print('end')


if __name__ == '__main__':
    run()
