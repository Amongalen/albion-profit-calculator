import copy
import json
import math
import re
from dataclasses import dataclass, field
from typing import List, NamedTuple

ITEM_NAMES_TXT_FILE = '../resources/item_names.txt'

ITEMS_JSON_FILE = '../resources/items.json'

CRAFTING_FAME_JSON_FILE = '../resources/crafting_fame.json'

ITEM_ID_KEY = '@uniquename'

FILTERED_OUT_CATEGORIES = {'luxurygoods', 'other', 'token', 'trophies', 'farmables'}
FILTERED_OUT_SUBCATEGORIES = {'unique', 'vanity', 'unique_shoes', 'unique_helmet', 'unique_armor', 'repairkit', 'flag',
                              'banner', 'decoration_furniture', 'morgana_furniture', 'keeper_furniture',
                              'heretic_furniture'}
WANTED_ITEM_TYPES = ['farmableitem', 'simpleitem', 'consumableitem', 'equipmentitem',
                     'weapon', 'mount', 'furnitureitem', 'journalitem']

Ingredient = NamedTuple('Ingredient', item_id=str, quantity=int, max_return_rate=int)


@dataclass(frozen=True)
class Recipe:
    CRAFTING_RECIPE = 'crafting'
    UPGRADE_RECIPE = 'upgrade'
    TRANSPORT_RECIPE = 'transport'

    result_item_id: str
    recipe_type: str
    result_quantity: int = 1
    silver_cost: int = 0
    ingredients: List[Ingredient] = field(default_factory=list)


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    subcategory: str
    base_item_id: str
    recipes: List[Recipe] = field(default_factory=list)
    crafting_fame: int = 0
    item_value: int = 0


def get_all_items_ids():
    return list(_items_data.keys())


def get_item_subcategory(item_id):
    return _items_data[item_id].subcategory


def get_all_recipes():
    return _recipes


def get_all_transport_recipes():
    return _transport_recipes


def get_all_upgrade_recipes():
    return _upgrade_recipes


def get_all_crafting_recipes():
    return _crafting_recipes


def get_item_name(item_id):
    return _items_data[item_id].name


def get_item_crafting_fame(item_id):
    return _items_data[item_id].crafting_fame


def load_items():
    raw_items_data = read_items_file()
    items_names = read_item_names_file()
    enchantment_items = pull_out_enchantments(raw_items_data)

    raw_items_data = raw_items_data | enchantment_items
    crafting_fame = read_crafting_fame_file()
    items = create_items(raw_items_data, items_names, crafting_fame)
    return items


def create_items(raw_items_data, items_names, crafting_fame):
    items = {}
    # there are some weird items without name, probably unused ones - lets remove those
    raw_items_data = {k: v for k, v in raw_items_data.items() if k in items_names}
    for item_id, item_data in raw_items_data.items():
        if not is_item_useful(item_data):
            continue
        name = items_names[item_id]
        category = item_data['@shopcategory']
        subcategory = item_data['@shopsubcategory1']
        recipes = extract_recipes(item_data)
        base_item_id = item_data.get('base_item_id', None)
        items[item_id] = Item(item_id, name, category, subcategory, base_item_id,
                              recipes, crafting_fame.get(item_id, 0))
        if 'JOURNAL' in item_id:
            empty_journal_id = item_id + '_EMPTY'
            empty_journal_name = items_names[empty_journal_id]
            items[empty_journal_id] = Item(empty_journal_id, empty_journal_name, category, subcategory, base_item_id,
                                           recipes)
            full_journal_id = item_id + '_FULL'
            full_journal_name = items_names[full_journal_id]
            items[full_journal_id] = Item(full_journal_id, full_journal_name, category, subcategory, base_item_id,
                                          recipes)
    return items


def extract_recipes(item):
    crafting_recipes = extract_recipes_details(item, is_upgrade_recipe=False)
    upgrade_recipes = extract_recipes_details(item, is_upgrade_recipe=True)
    item_id = add_missing_at_symbol(item[ITEM_ID_KEY])
    transport_recipe = [Recipe(item_id, Recipe.TRANSPORT_RECIPE,
                               ingredients=[Ingredient(item_id, 1, 0)])]
    return crafting_recipes + upgrade_recipes + transport_recipe


def extract_recipes_details(item, is_upgrade_recipe):
    data_source = 'upgraderequirements' if is_upgrade_recipe else 'craftingrequirements'
    recipes_data = item.get(data_source, None)
    recipes_data = recipes_data if isinstance(recipes_data, list) else [recipes_data]
    recipes_details = [recipe for recipe_data in recipes_data
                       if (recipe := extract_single_recipe_details(recipe_data, item, is_upgrade_recipe))
                       is not None]

    return recipes_details


def extract_single_recipe_details(recipe_data, item, is_upgrade_recipe):
    if recipe_data is None:
        return None
    data_source = 'upgraderesource' if is_upgrade_recipe else 'craftresource'
    craft_resources = recipe_data.get(data_source, None)
    if craft_resources is None:
        return None

    recipe_type = Recipe.UPGRADE_RECIPE if is_upgrade_recipe else Recipe.CRAFTING_RECIPE
    result_item_id = add_missing_at_symbol(item[ITEM_ID_KEY])
    result_quantity = int(recipe_data.get('@amountcrafted', 1))
    silver_cost = int(recipe_data.get('@silver', 0))

    craft_resources = craft_resources if isinstance(craft_resources, list) else [craft_resources]

    ingredients = [Ingredient(add_missing_at_symbol(x[ITEM_ID_KEY]),
                              int(x['@count']), float(x.get('@maxreturnamount', math.inf)))
                   for x in craft_resources]
    if is_upgrade_recipe:
        base_item_ingredient = Ingredient(item['base_item_id'], 1, math.inf)
        ingredients.append(base_item_ingredient)

    return Recipe(result_item_id, recipe_type, result_quantity, silver_cost, ingredients)


def pull_out_enchantments(raw_items_data):
    enchantment_items = {}
    for v in raw_items_data.values():
        enchantments = v.get('enchantments', {}).get('enchantment', None)
        if enchantments is None:
            continue
        enchantments = enchantments if isinstance(enchantments, list) else [enchantments]

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
            enchantment_items[new_id] = new_item

    return enchantment_items


def is_item_useful(item):
    category = item['@shopcategory']
    subcategory = item['@shopsubcategory1']
    if category in FILTERED_OUT_CATEGORIES and not subcategory == 'royalsigils':
        return False
    if subcategory in FILTERED_OUT_SUBCATEGORIES:
        return False
    if category == 'furniture' and item[ITEM_ID_KEY].startswith('UNIQUE'):
        return False
    return True


def read_crafting_fame_file():
    with open(CRAFTING_FAME_JSON_FILE) as f:
        crafting_fame = json.load(f)
    return {key: value for key, value in crafting_fame.items() if value is not None}


def read_items_file():
    with open(ITEMS_JSON_FILE) as f:
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


def read_item_names_file():
    items_names = {}
    with open(ITEM_NAMES_TXT_FILE) as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 3:
                item_id = parts[1].strip()
                item_name = parts[2].strip()
                items_names[item_id] = item_name
    return items_names


def load_recipes():
    return [recipe for item in _items_data.values() for recipe in item.recipes]


def get_items_ids_for_category_or_subcategory(*args):
    return [item_id for item_id, item in _items_data.items()
            if item.subcategory in args
            or item.category in args]


_items_data = load_items()
_recipes = load_recipes()
_crafting_recipes = [recipe for recipe in _recipes if recipe.recipe_type == Recipe.CRAFTING_RECIPE]
_upgrade_recipes = [recipe for recipe in _recipes if recipe.recipe_type == Recipe.UPGRADE_RECIPE]
_transport_recipes = [recipe for recipe in _recipes if recipe.recipe_type == Recipe.TRANSPORT_RECIPE]
