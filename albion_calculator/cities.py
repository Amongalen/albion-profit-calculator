import bidict as bidict

_CITIES = bidict.bidict(
    {0: 'Fort Sterling', 1: 'Lymhurst', 2: 'Bridgewatch', 3: 'Martlock', 4: 'Thetford', 5: 'Caerleon'})


def index_of_city(name):
    return _CITIES.inverse[name]


def city_at_index(index):
    return _CITIES[index]


def cities_names():
    return sorted(list(_CITIES.values()), key=index_of_city)


