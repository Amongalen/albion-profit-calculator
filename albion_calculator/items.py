import json
from collections import defaultdict

filtered_categories = {'luxurygoods', 'other', 'token', 'trophies', 'farmables'}
filtered_subcategories = {'unique', 'vanity', 'unique_shoes', 'unique_helmet', 'unique_armor', 'repairkit', 'flag',
                          'banner', 'decoration_furniture', 'morgana_furniture', 'keeper_furniture',
                          'heretic_furniture'}


def is_item_useful(item):
    category = item['@shopcategory']
    subcategory = item['@shopsubcategory1']
    if category in filtered_categories and not subcategory == 'royalsigils':
        return False
    if subcategory in filtered_subcategories:
        return False
    if category == 'furniture' and item['@uniquename'].startswith('UNIQUE'):
        return False
    return True


if __name__ == '__main__':
    with open('../resources/items.json') as f:
        items = json.load(f)
        items = items['items']
    item_types = ['farmableitem', 'simpleitem', 'consumableitem', 'equipmentitem',
                  'weapon', 'mount', 'furnitureitem', 'journalitem']
    items_list = [item for item_type in item_types for item in items[item_type] if is_item_useful(item)]
    items_by_category = defaultdict(list)
    for item in items_list:
        category = item.get('@shopcategory')
        items_by_category[category].append(item)

    items_by_subcategory = defaultdict(list)
    for item in items_list:
        subcategory = item.get('@shopsubcategory1')
        items_by_subcategory[subcategory].append(item)

    print('end')
