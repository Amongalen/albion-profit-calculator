from math import nan

import numpy as np

from albion_calculator import prices, items

# MATRIX[transport_from][transport_to]
from albion_calculator.prices import get_prices_for_item

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

NO_TRAVEL_MULTIPLIER = np.array([
    [1.00, nan, nan, nan, nan, nan],
    [nan, 1.00, nan, nan, nan, nan],
    [nan, nan, 1.00, nan, nan, nan],
    [nan, nan, nan, 1.00, nan, nan],
    [nan, nan, nan, nan, 1.00, nan],
    [nan, nan, nan, nan, nan, 1.00]
])


def calculate_profit_for_recipe(recipe, multiplier, use_focus):
    product_price = get_prices_for_item(recipe.result_item_id)
    ingredients_prices = {
        ingredient.item_id: get_prices_for_item(ingredient.item_id) * ingredient.quantity
        for ingredient in recipe.ingredients}

    result_value = product_price / multiplier

    print(result_value)


if __name__ == '__main__':
    items = items.load_items()

    t5_planks = items['T5_PLANKS']
    recipe = t5_planks.recipes[0]
    items_ids = ['T5_WOOD', 'T5_PLANKS', 'T4_PLANKS']
    calculate_profit_for_recipe(recipe, NO_TRAVEL_MULTIPLIER, use_focus=False)
    get_prices_for_item('T5_PLANKS')
    print('end')
