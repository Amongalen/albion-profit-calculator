import json

import bidict as bidict

BASE_CRAFTING_RATE = 0.18

CITIES = bidict.bidict(
    {0: 'Fort Sterling', 1: 'Lymhurst', 2: 'Bridgewatch', 3: 'Martlock', 4: 'Thetford', 5: 'Caerleon'})

CLUSTER_ID = {'0000': 'Thetford', '1000': 'Lymhurst', '2000': 'Bridgewatch',
              '3004': 'Martlock', '4000': 'Fort Sterling', '3003': 'Caerleon'}


def index_of_city(name):
    return CITIES.inverse[name]


def city_at_index(index):
    return CITIES[index]


def cities_names():
    return sorted(list(CITIES.values()), key=index_of_city)


def load_crafting_modifiers_file():
    with open('../resources/craftingmodifiers.json') as f:
        raw_crafting_modifiers_data = json.load(f)
    return raw_crafting_modifiers_data['craftingmodifiers']['craftinglocation']


def load_crafting_modifiers():
    raw_data = load_crafting_modifiers_file()
    crafting_modifiers = {}
    for location in raw_data:
        city = CLUSTER_ID.get(location['@clusterid'], None)
        if city is None:
            continue
        crafting_modifiers[city] = {modifier['@name']: float(modifier['@value']) for modifier in
                                    location['craftingmodifiers']}
    return crafting_modifiers


return_rates = load_crafting_modifiers()


def get_return_rate(city, item_category):
    return return_rates[city].get(item_category, 0) + BASE_CRAFTING_RATE
