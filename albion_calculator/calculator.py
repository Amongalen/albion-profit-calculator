from math import nan, inf

import numpy as np

from albion_calculator.cities import CITIES, index_of_city
from albion_calculator import prices, items

# MATRIX[transport_from][transport_to]
TRAVEL_COST_MULTIPLIER = np.array([
    [1.00, 1.05, 1.10, 1.10, 1.05, 1.05],
    [1.05, 1.00, 1.05, 1.10, 1.10, 1.05],
    [1.10, 1.05, 1.00, 1.05, 1.10, 1.05],
    [1.10, 1.10, 1.05, 1.00, 1.05, 1.05],
    [1.05, 1.10, 1.10, 1.05, 1.00, 1.05],
    [1.05, 1.05, 1.05, 1.05, 1.05, 1.00]
])
TRAVEL_COST_NO_RISK_MULTIPLIER = np.array([
    [1.00, 1.05, 1.10, 1.10, 1.05, nan],
    [1.05, 1.00, 1.05, 1.10, 1.10, nan],
    [1.10, 1.05, 1.00, 1.05, 1.10, nan],
    [1.10, 1.10, 1.05, 1.00, 1.05, nan],
    [1.05, 1.10, 1.10, 1.05, 1.00, nan],
    [nan, nan, nan, nan, nan, 1.00]
])
empty = np.empty((6, 6))
empty[:] = nan
NO_TRAVEL_MULTIPLIER = np.fill_diagonal(empty, 1)


def calculate_profit_for_recipe(recipe, prices_data, multiplier, use_focus):
    product_price = get_prices_in_cities(recipe.result_item_id, prices_data)
    ingredients_prices = {
        ingredient.item_id: get_prices_in_cities(ingredient.item_id, prices_data) * ingredient.quantity
        for ingredient in recipe.ingredients}

    result_value = product_price / multiplier

    print(result_value)


def get_prices_in_cities(item_id, prices_data):
    result = []
    prices_sorted_by_city = sorted(prices_data[item_id].items(), key=lambda x: index_of_city(x[0]))
    for _, record in prices_sorted_by_city:
        if not record:
            result.append(nan)
            continue
        min_price = record['sell_price_min']
        avg_price_24h = record['avg_price_24h']
        if min_price != 0:
            price = min_price
        elif avg_price_24h != 0:
            price = avg_price_24h
        else:
            price = nan
        result.append(price)
    return np.array(result)


if __name__ == '__main__':
    items = items.load_items()

    t5_planks = items['T5_PLANKS']
    recipe = t5_planks.recipes[0]
    items_ids = ['T5_WOOD', 'T5_PLANKS', 'T4_PLANKS']
    prices_data = prices.get_all_prices(items_ids)
    calculate_profit_for_recipe(recipe, prices_data, NO_TRAVEL_MULTIPLIER)
    get_prices_in_cities('T5_PLANKS', prices_data)
    print('end')
