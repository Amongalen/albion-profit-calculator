import json
import pathlib

from albion_calculator import items, craftingmodifiers

_CATEGORIES_FILENAME = pathlib.Path(__file__).parent /'resources/shop_categories.json'


def get_category_pretty_name(category_id: str) -> str:
    return _category_pretty_names.get(category_id.upper(), '')


def get_craftable_shop_categories() -> list[str]:
    return [category for category in _shop_categories if
            category in craftingmodifiers.get_craftable_categories()]


def _load_shop_subcategories() -> list[str]:
    items_json = _read_items_file()
    categories = items_json['items']['shopcategories']['shopcategory']
    return [subcategory['@id'] for category in categories for subcategory in category['shopsubcategory']]


def _read_items_file() -> dict:
    with open(items.ITEMS_JSON_FILE) as f:
        return json.load(f)


def _read_localization_file() -> dict:
    with open('resources/localization.json', encoding='utf8') as f:
        return json.load(f)


def _extract_localizations_starting_with(prefix: str) -> dict[str, str]:
    localization_json = _read_localization_file()
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


def _write_to_file(localizations: dict) -> None:
    with open(_CATEGORIES_FILENAME, 'w') as f:
        json.dump(localizations, f, indent=1)


def _load_category_pretty_names() -> dict:
    with open(_CATEGORIES_FILENAME, 'r') as f:
        return json.load(f)


_category_pretty_names = _load_category_pretty_names()
_shop_categories = _load_shop_subcategories()

# moving categories to separate file so don't have to bother with huge localizations file
if __name__ == '__main__':
    subcategories = _extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPSUBCATEGORY_')
    categories = _extract_localizations_starting_with('@MARKETPLACEGUI_ROLLOUT_SHOPCATEGORY_')
    _write_to_file(subcategories | categories)
