from math import nan

import numpy as np

from albion_calculator import items, cities, journals, prices, craftingmodifiers

# MATRIX[transport_to][transport_from]
from albion_calculator.items import Recipe
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


# @todo refactor this crap
def calculate_profit_details_for_recipe(recipe, multiplier, use_focus):
    ingredients_costs = calculate_ingredients_costs(multiplier, recipe, use_focus)
    missing_ingredients = check_missing_ingredients_prices(ingredients_costs, recipe)
    if missing_ingredients:
        return {'missing_ingredients': missing_ingredients}

    final_profit_matrix = calculate_final_profit_matrix(ingredients_costs, multiplier, recipe)

    max_profit_index = np.unravel_index(np.nanargmax(final_profit_matrix), final_profit_matrix.shape)
    destination_city_index = max_profit_index[0]
    production_city_index = max_profit_index[1]
    max_profit = np.nanmax(final_profit_matrix)

    journal_profit_details = calculate_journal_profit(recipe.result_item_id)
    final_profit = max_profit + journal_profit_details['journals_profit']

    ingredients_details = []
    for item_id, data in ingredients_costs[production_city_index].items():
        quantity = next(ingredient.quantity for ingredient in recipe.ingredients if ingredient.item_id == item_id)
        local_price = get_price_for_item_in_city(item_id, data[1])
        total_cost = quantity * local_price
        total_cost_with_transport = total_cost * multiplier[data[1]][production_city_index]
        ingredients_details.append({
            'ingredient_item_id': item_id,
            'local_price': round(local_price, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_with_transport': round(total_cost_with_transport, 2),
            'total_cost_with_returns': round(data[0], 2),
            'source_city': cities.city_at_index(data[1]),
            'quantity': quantity
        })

    final_product_price = get_price_for_item_in_city(recipe.result_item_id, destination_city_index)
    max_profit_details = {
        'product': recipe.result_item_id,
        'product_quantity': recipe.result_quantity,
        'profit_without_journals': round(max_profit, 2),
        'profit_with_journals': round(final_profit, 2),
        'profit_per_journal': round(journal_profit_details['profit_per_journal'], 2),
        'journals_filled': round(journal_profit_details['journals_filled'], 2),
        'destination_city': cities.city_at_index(destination_city_index),
        'production_city': cities.city_at_index(production_city_index),
        'final_product_price': round(final_product_price, 2),
        'ingredients_details': ingredients_details,
        'ingredients_total_cost': sum(ingredient['total_cost_with_returns'] for ingredient in ingredients_details)
    }
    return max_profit_details


def calculate_journal_profit(item_id):
    journal = journals.get_journal_for_item(item_id)
    if journal is None:
        return {'journals_profit': 0, 'profit_per_journal': 0, 'journals_filled': 0}
    crafting_fame = items.get_item_crafting_fame(item_id)
    full_journal_price = prices.get_avg_price_for_item(journal['item_id'] + '_FULL')
    empty_journal_price = journal['cost']
    if np.isnan(full_journal_price) or empty_journal_price == 0:
        return {'journals_profit': 0, 'profit_per_journal': 0, 'journals_filled': 0}
    profit_per_journal = full_journal_price - empty_journal_price
    journals_filled = crafting_fame / journal['max_fame']
    return {'journals_profit': profit_per_journal * journals_filled,
            'profit_per_journal': profit_per_journal,
            'journals_filled': journals_filled}


def check_missing_ingredients_prices(ingredients_costs, recipe):
    return [ingredient.item_id for ingredient in recipe.ingredients
            if are_all_prices_nan(ingredients_costs, ingredient.item_id)]


def are_all_prices_nan(ingredients_costs, item_id):
    return all(np.isnan(city[item_id][0]) for city in ingredients_costs)


def find_ingredients_best_deals_per_city(ingredients_price_matrices):
    return [{item_id: find_ingredient_best_deal_for_city(city, price_matrix)
             for item_id, price_matrix in ingredients_price_matrices.items()}
            for city in range(6)]


def find_ingredient_best_deal_for_city(city, price_matrix):
    min_price = np.nanmin(price_matrix[city])
    index = np.nanargmin(price_matrix[city]) if not np.isnan(min_price) else nan
    return min_price, index


def calculate_final_profit_matrix(ingredients_costs, multiplier, recipe):
    ingredients_costs_total = [sum(item[0] for item in city.values()) for city in ingredients_costs]
    product_price = get_prices_for_item(recipe.result_item_id)
    return (product_price * recipe.result_quantity / multiplier).T - ingredients_costs_total


def calculate_ingredients_costs(multiplier, recipe, use_focus):
    return_rates = craftingmodifiers.get_return_rates_vector(recipe.result_item_id, use_focus)
    ingredients_price_matrices = {
        ingredient.item_id: calculate_single_ingredient_cost(ingredient, multiplier, recipe.recipe_type, return_rates)
        for ingredient in recipe.ingredients}
    ingredients_costs = find_ingredients_best_deals_per_city(ingredients_price_matrices)
    return ingredients_costs


def calculate_single_ingredient_cost(ingredient, multiplier, recipe_type, return_rates):
    price_matrix = get_prices_for_item(ingredient.item_id) * ingredient.quantity * multiplier
    if recipe_type == Recipe.CRAFTING_RECIPE and ingredient.max_return_rate != 0:
        price_matrix = price_matrix * return_rates
    return price_matrix


if __name__ == '__main__':
    items_data = items.load_items()

    T5_MAIN_SWORD = items_data['T5_MAIN_SWORD']
    recipe = T5_MAIN_SWORD.recipes[0]

    result = calculate_profit_details_for_recipe(recipe, TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)
    print('end')
