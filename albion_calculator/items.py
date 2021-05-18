import copy
import json
import math
import re
from dataclasses import dataclass, field
from typing import List, NamedTuple

ITEM_ID_KEY = '@uniquename'

FILTERED_CATEGORIES = {'luxurygoods', 'other', 'token', 'trophies', 'farmables'}
FILTERED_SUBCATEGORIES = {'unique', 'vanity', 'unique_shoes', 'unique_helmet', 'unique_armor', 'repairkit', 'flag',
                          'banner', 'decoration_furniture', 'morgana_furniture', 'keeper_furniture',
                          'heretic_furniture'}
WANTED_ITEM_TYPES = ['farmableitem', 'simpleitem', 'consumableitem', 'equipmentitem',
                     'weapon', 'mount', 'furnitureitem', 'journalitem']

Ingredient = NamedTuple('Ingredient', item_id=str, quantity=int, max_return_rate=int)


@dataclass(frozen=True)
class Recipe:
    CRAFTING_RECIPE = 'crafting'
    UPGRADE_RECIPE = 'upgrade'

    result_item_id: str
    recipe_type: str
    result_quantity: int = 0
    silver_cost: int = 0
    ingredients: List[Ingredient] = field(default_factory=list)


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    subcategory: str
    base_item_id: str = None
    recipes: List[Recipe] = field(default_factory=list)
    item_value: int = 0


def load_items():
    raw_items_data = load_items_file()
    items_names = load_item_names()
    enchantment_items = pull_out_enchantments(raw_items_data)

    raw_items_data = raw_items_data | enchantment_items
    items = create_items(raw_items_data, items_names)
    return items


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
        all_recipes = extract_recipes(item_data)
        base_item_id = item_data.get('base_item_id', None)
        item = Item(item_id, name, category, subcategory, base_item_id, all_recipes)
        items[item_id] = item

    return items


def extract_recipes(item):
    recipes = []

    crafting_recipes_data = item.get('craftingrequirements', None)
    if not isinstance(crafting_recipes_data, list):
        crafting_recipes_data = [crafting_recipes_data]

    for recipe_data in crafting_recipes_data:
        if recipe_data is not None:
            recipe = extract_recipe_details(recipe_data, item, is_upgrade_recipe=False)
            if recipe is not None:
                recipes.append(recipe)

    upgrade_recipes_data = item.get('upgraderequirements', None)
    if not isinstance(upgrade_recipes_data, list):
        upgrade_recipes_data = [upgrade_recipes_data]

    for recipe_data in upgrade_recipes_data:
        if recipe_data is not None:
            recipe = extract_recipe_details(recipe_data, item, is_upgrade_recipe=True)
            if recipe is not None:
                recipes.append(recipe)

    return recipes


def extract_recipe_details(recipe_data, item, is_upgrade_recipe):
    if is_upgrade_recipe:
        craft_resources = recipe_data.get('upgraderesource', None)
    else:
        craft_resources = recipe_data.get('craftresource', None)
    if craft_resources is None:
        return

    result_item_id = item[ITEM_ID_KEY]
    result_item_id = add_missing_at_symbol(result_item_id)
    result_quantity = int(recipe_data.get('@amountcrafted', 1))
    silver_cost = int(recipe_data.get('@silver', 0))

    if not isinstance(craft_resources, list):
        craft_resources = [craft_resources]

    ingredients = [Ingredient(x[ITEM_ID_KEY], int(x['@count']), float(x.get('@maxreturnamount', math.inf))) for x in
                   craft_resources]
    if is_upgrade_recipe:
        base_item_ingredient = Ingredient(item['base_item_id'], 1, math.inf)
        ingredients.append(base_item_ingredient)

    recipe_type = Recipe.UPGRADE_RECIPE if is_upgrade_recipe else Recipe.CRAFTING_RECIPE
    return Recipe(result_item_id, recipe_type, result_quantity, silver_cost, ingredients)


def pull_out_enchantments(raw_items_data):
    new_items = {}
    for k, v in raw_items_data.items():
        enchantments = v.get('enchantments', {}).get('enchantment', None)
        if enchantments is not None:
            if not isinstance(enchantments, list):
                enchantments = [enchantments]

            for enchantment in enchantments:
                new_item = copy.copy(v)
                new_item.pop('craftingrequirements', None)
                new_item.pop('enchantments', None)
                new_item.pop('upgraderequirements', None)
                new_item['craftingrequirements'] = enchantment['craftingrequirements']
                new_item['upgraderequirements'] = enchantment['upgraderequirements']
                new_id = new_item[ITEM_ID_KEY] + '@' + enchantment['@enchantmentlevel']
                new_item[ITEM_ID_KEY] = new_id
                new_item['base_item_id'] = v[ITEM_ID_KEY]
                new_items[new_id] = new_item

    return new_items


def is_item_useful(item):
    category = item['@shopcategory']
    subcategory = item['@shopsubcategory1']
    if category in FILTERED_CATEGORIES and not subcategory == 'royalsigils':
        return False
    if subcategory in FILTERED_SUBCATEGORIES:
        return False
    if category == 'furniture' and item[ITEM_ID_KEY].startswith('UNIQUE'):
        return False
    return True


def load_items_file():
    with open('../resources/items.json') as f:
        raw_items_data = json.load(f)
        raw_items_data = raw_items_data['items']
    items = {add_missing_at_symbol(item[ITEM_ID_KEY]): item for item_type in WANTED_ITEM_TYPES for item in
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


def load_item_names():
    items_names = {}
    with open('../resources/item_names.txt') as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 3:
                item_id = parts[1].strip()
                item_name = parts[2].strip()
                items_names[item_id] = item_name
    return items_names
