import bidict as bidict

CITIES = bidict.bidict(
    {0: 'Fort Sterling', 1: 'Lymhurst', 2: 'Bridgewatch', 3: 'Martlock', 4: 'Thetford', 5: 'Caerleon'})


def index_of_city(name):
    return CITIES.inverse[name]


def city_at_index(index):
    return CITIES[index]


def cities_names():
    return sorted(list(CITIES.values()), key=index_of_city)


