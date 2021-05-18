from math import nan

import numpy as np

from albion_calculator import items, cities

# MATRIX[transport_to][transport_from]
from albion_calculator.prices import get_prices_for_item, get_price_for_item_in_city

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


# @todo product quantity; limited return rate
# @todo cost without return rate
# @todo refactor this crap
def calculate_profit_details_for_recipe(recipe, multiplier, use_focus):
    ingredients_costs = calculate_ingredients_costs(multiplier, recipe, use_focus)
    final_profit_matrix = calculate_final_profit_matrix(ingredients_costs, multiplier, recipe)

    max_profit_index = np.unravel_index(np.nanargmax(final_profit_matrix), final_profit_matrix.shape)
    destination_city_index = max_profit_index[0]
    production_city_index = max_profit_index[1]
    max_profit = np.nanmax(final_profit_matrix)

    details1 = {}
    for item_id, data in ingredients_costs[production_city_index].items():
        quantity = next(ingredient.quantity for ingredient in recipe.ingredients if ingredient.item_id == item_id)
        local_price = round(get_price_for_item_in_city(item_id, data[1]), 2)
        details1[item_id] = {
            'local_price': local_price,
            'total_price': quantity * local_price,
            'total_crafting_cost_with_returns': round(data[0], 2),
            'source_city': cities.city_at_index(data[1]),
            'quantity': quantity
        }
    ingredients_details = details1

    final_product_price = get_price_for_item_in_city(recipe.result_item_id, destination_city_index)
    details = {
        'max_profit': max_profit,
        'destination_city': cities.city_at_index(destination_city_index),
        'production_city': cities.city_at_index(production_city_index),
        'final_product_price': final_product_price,
        'ingredients_details': ingredients_details
    }
    max_profit_details = details
    return max_profit_details


def find_ingredients_best_deals_per_city(ingredients_price_matrices):
    result = []
    for city in range(6):
        best_deals = {}
        for item_id, price_matrix in ingredients_price_matrices.items():
            min_price = np.nanmin(price_matrix[city])
            index = np.nanargmin(price_matrix[city])
            best_deals[item_id] = (min_price, index)
        result.append(best_deals)
    return result


def calculate_final_profit_matrix(ingredients_costs, multiplier, recipe):
    ingredients_costs_total = [sum(item[0] for item in city.values()) for city in ingredients_costs]
    product_price = get_prices_for_item(recipe.result_item_id)
    final_profit_matrix = (product_price / multiplier).T - ingredients_costs_total
    return final_profit_matrix


def calculate_ingredients_costs(multiplier, recipe, use_focus):
    ingredients_price_matrices = {}
    return_rates = cities.get_return_rates_vector(recipe.result_item_id, use_focus)
    for ingredient in recipe.ingredients:
        price_matrix = get_prices_for_item(ingredient.item_id) * ingredient.quantity * multiplier \
                       * np.atleast_2d((1 - return_rates)).T
        ingredients_price_matrices[ingredient.item_id] = price_matrix
    ingredients_costs = find_ingredients_best_deals_per_city(ingredients_price_matrices)
    return ingredients_costs


if __name__ == '__main__':
    items = items.load_items()

    t5_planks = items['T5_PLANKS']
    recipe = t5_planks.recipes[0]
    items_ids = ['T5_WOOD', 'T5_PLANKS', 'T4_PLANKS']
    result = calculate_profit_details_for_recipe(recipe, TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)
    get_prices_for_item('T5_PLANKS')
    print('end')
