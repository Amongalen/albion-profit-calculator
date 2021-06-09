import json

from albion_calculator import items, craftingmodifiers

CATEGORIES_FILENAME = 'resources/shop_categories.json'


def load_shop_subcategories():
    items_json = read_items_file()
    categories = items_json['items']['shopcategories']['shopcategory']
    return [subcategory['@id'] for category in categories for subcategory in category['shopsubcategory']]


def read_items_file():
    with open(items.ITEMS_JSON_FILE) as f:
        return json.load(f)


def read_localization_file():
    with open('resources/localization.json', encoding='utf8') as f:
        return json.load(f)


def extract_localizations_starting_with(prefix):
    localization_json = read_localization_file()
    records = localization_json['tmx']['body']['tu']
    subcategory_records = [record for record in records if
                           record['@tuid'].startswith(prefix)]
    result = {}
    for record in subcategory_records:
        name = record['@tuid'][len(prefix):]
        localizations = record['tuv']
        localizations = localizations if isinstance(localizations, list) else [localizations]
        eng_localization = [localization['seg'] for localization in localizations
                            if localization['@xml:lang'] == 'EN-US'][0]
        result[name] = eng_localization
    return result


def write_to_file(localizations):
    with open(CATEGORIES_FILENAME, 'w') as f:
        json.dump(localizations, f, indent=1)


def load_category_pretty_names():
    with open(CATEGORIES_FILENAME, 'r') as f:
        return json.load(f)


def get_category_pretty_name(category_id):
    return _category_pretty_names.get(category_id.upper(), '')


def get_craftable_shop_categories():
    return [category for category in _shop_categories if
            category in craftingmodifiers.get_craftable_categories()]


_category_pretty_names = load_category_pretty_names()
_shop_categories = load_shop_subcategories()

# moving categories to separate file so don't have to bother with huge localizations file
if __name__ == '__main__':
    subcategories = extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPSUBCATEGORY_')
    categories = extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPCATEGORY_')
    write_to_file(subcategories | categories)
