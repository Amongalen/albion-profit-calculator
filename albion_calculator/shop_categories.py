import json

from albion_calculator import items

CATEGORIES_FILENAME = 'resources/shop_categories.json'


def load_localization_json():
    with open('resources/localization.json', encoding='utf8') as f:
        return json.load(f)


def extract_localizations_starting_with(prefix):
    localization_json = load_localization_json()
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


def load_categories():
    with open(CATEGORIES_FILENAME, 'r') as f:
        return json.load(f)


def get_category_pretty_name(category_id):
    return _shop_categories.get(category_id, '')


_shop_categories = load_categories()

# moving categories to separate file so don't have to bother with huge localizations file
if __name__ == '__main__':
    subcategories = extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPSUBCATEGORY_')
    categories = extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPCATEGORY_')
    write_to_file(subcategories | categories)
