_CITIES = ['Fort Sterling', 'Lymhurst', 'Bridgewatch', 'Martlock', 'Thetford', 'Caerleon']


def city_at_index(index: int) -> str:
    return _CITIES[index]


def cities_names() -> list[str]:
    return _CITIES[:]
