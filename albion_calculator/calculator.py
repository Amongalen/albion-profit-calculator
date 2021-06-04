import datetime
import time
from datetime import timedelta
from math import nan

import numpy as np
import tqdm

from albion_calculator import items, cities, journals, prices, craftingmodifiers

# MATRIX[transport_to][transport_from]
from albion_calculator.items import Recipe
from albion_calculator.prices import get_prices_for_item, get_price_for_item_in_city

UPGRADE_TRAVEL = 'UPGRADE_TRAVEL'

UPGRADE_NO_RISK = 'UPGRADE_NO_RISK'

UPGRADE_NO_TRAVEL = 'UPGRADE_NO_TRAVEL'

UPGRADE_PER_CITY = 'UPGRADE_PER_CITY'

TRANSPORT_NO_RISK = 'TRANSPORT_NO_RISK'

TRANSPORT = 'TRANSPORT'

CRAFTING_NO_RISK_WITH_FOCUS = 'CRAFTING_NO_RISK_WITH_FOCUS'

CRAFTING_TRAVEL_NO_FOCUS = 'CRAFTING_TRAVEL_NO_FOCUS'

CRAFTING_TRAVEL_WITH_FOCUS = 'CRAFTING_TRAVEL_WITH_FOCUS'

CRAFTING_NO_RISK_NO_FOCUS = 'CRAFTING_NO_RISK_NO_FOCUS'

CRAFTING_NO_TRAVEL_WITH_FOCUS = 'CRAFTING_NO_TRAVEL_WITH_FOCUS'

CRAFTING_PER_CITY_WITH_FOCUS = 'CRAFTING_PER_CITY_WITH_FOCUS'

CRAFTING_PER_CITY_NO_FOCUS = 'CRAFTING_PER_CITY_NO_FOCUS'

CRAFTING_NO_TRAVEL_NO_FOCUS = 'CRAFTING_NO_TRAVEL_NO_FOCUS'

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


def one_city_multipliers():
    arrays = []
    for i in range(6):
        array = np.empty((6, 6))
        array[:] = nan
        array[i][i] = 1
        arrays.append(array)
    return arrays


ONE_CITY_ONLY_MULTIPLIERS = one_city_multipliers()


def check_missing_ingredients_prices(recipe, multiplier):
    return [ingredient.item_id for ingredient in recipe.ingredients
            if np.isnan(prices.get_prices_for_item(ingredient.item_id) * multiplier).all()]


def calculate_profit_details_for_recipe(recipe, multiplier, use_focus):
    missing_ingredients = check_missing_ingredients_prices(recipe, multiplier)
    if missing_ingredients:
        return {'missing_item_price': missing_ingredients}
    ingredients_best_deals = calculate_ingredients_best_deals(multiplier, recipe, use_focus)

    final_profit_matrix = calculate_final_profit_matrix(ingredients_best_deals, multiplier, recipe)
    if np.isnan(final_profit_matrix).all():
        return {'missing_item_price': recipe.result_item_id}

    journal_profit_details = calculate_journal_profit(recipe.result_item_id)
    profit_summary = summarize_profit(final_profit_matrix, ingredients_best_deals, journal_profit_details, multiplier,
                                      recipe)
    return profit_summary


def summarize_profit(final_profit_matrix, ingredients_costs, journal_profit_details, multiplier, recipe):
    max_profit = np.nanmax(final_profit_matrix)
    final_profit = max_profit + journal_profit_details['journals_profit']
    destination_city_index, production_city_index = np.unravel_index(np.nanargmax(final_profit_matrix),
                                                                     final_profit_matrix.shape)
    ingredients_details = summarize_ingredient_details(ingredients_costs, multiplier, production_city_index, recipe)
    final_product_price = get_price_for_item_in_city(recipe.result_item_id, destination_city_index)
    ingredients_total_cost = sum(ingredient['total_cost_with_returns'] for ingredient in ingredients_details)
    max_profit_details = {
        'product': recipe.result_item_id,
        'product_quantity': recipe.result_quantity,
        'profit_without_journals': round(max_profit, 2),
        'profit_with_journals': round(final_profit, 2),
        'profit_per_journal': round(journal_profit_details['profit_per_journal'], 2),
        'profit_percentage': round(final_profit / ingredients_total_cost, 2),
        'journals_filled': round(journal_profit_details['journals_filled'], 2),
        'destination_city': cities.city_at_index(destination_city_index),
        'production_city': cities.city_at_index(production_city_index),
        'final_product_price': round(final_product_price, 2),
        'ingredients_details': ingredients_details,
        'ingredients_total_cost': ingredients_total_cost
    }
    return max_profit_details


def summarize_ingredient_details(ingredients_costs, multiplier, production_city_index, recipe):
    ingredients_details = []
    for ingredient in recipe.ingredients:
        item_id = ingredient.item_id
        price_with_returns, import_from = ingredients_costs[production_city_index][item_id]
        quantity = ingredient.quantity
        local_price = get_price_for_item_in_city(item_id, import_from)
        total_cost = quantity * local_price
        total_cost_with_transport = total_cost * multiplier[import_from][production_city_index]
        ingredients_details.append({
            'ingredient_item_id': item_id,
            'local_price': round(local_price, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_with_transport': round(total_cost_with_transport, 2),
            'total_cost_with_returns': round(price_with_returns, 2),
            'source_city': cities.city_at_index(import_from),
            'quantity': quantity
        })
    return ingredients_details


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


def find_ingredients_best_deals_per_city(ingredients_price_matrices):
    return [{item_id: find_ingredient_best_deal_for_city(city, price_matrix)
             for item_id, price_matrix in ingredients_price_matrices.items()}
            for city in range(6)]


def find_ingredient_best_deal_for_city(city, price_matrix):
    if np.isnan(price_matrix[city]).all():
        return nan, nan
    index = np.nanargmin(price_matrix[city])
    return price_matrix[city][index], index


def calculate_final_profit_matrix(ingredients_costs, multiplier, recipe):
    ingredients_costs_total = [sum(item[0] for item in city.values()) for city in ingredients_costs]
    product_price = get_prices_for_item(recipe.result_item_id)
    return (product_price * recipe.result_quantity / multiplier).T - ingredients_costs_total


def calculate_ingredients_best_deals(multiplier, recipe, use_focus):
    return_rates = craftingmodifiers.get_return_rates_vector(recipe.result_item_id, use_focus)
    ingredients_price_matrices = {
        ingredient.item_id: calculate_single_ingredient_cost(ingredient, multiplier, recipe.recipe_type, return_rates)
        for ingredient in recipe.ingredients}
    ingredients_best_deals = find_ingredients_best_deals_per_city(ingredients_price_matrices)
    return ingredients_best_deals


def calculate_single_ingredient_cost(ingredient, multiplier, recipe_type, return_rates):
    price_matrix = get_prices_for_item(ingredient.item_id) * ingredient.quantity * multiplier
    if recipe_type == Recipe.CRAFTING_RECIPE and ingredient.max_return_rate != 0:
        price_matrix = price_matrix * return_rates
    return price_matrix


calculations = {}


def initialize_or_update_calculations():
    global calculations
    prices.update_prices()
    update_crafting_calculations()
    update_transport_calculations()
    update_upgrade_calculations()


def update_upgrade_calculations():
    global calculations
    calculations[UPGRADE_PER_CITY] = calculate_local_per_city(items.get_all_upgrade_recipes(), use_focus=False)
    calculations[UPGRADE_NO_TRAVEL] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                    NO_TRAVEL_MULTIPLIER, use_focus=False)
    calculations[UPGRADE_NO_RISK] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                  TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)
    calculations[UPGRADE_TRAVEL] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                 TRAVEL_COST_MULTIPLIER, use_focus=False)


def update_transport_calculations():
    global calculations
    calculations[TRANSPORT] = calculate_profits_for_recipes(items.get_all_transport_recipes(),
                                                            TRAVEL_COST_MULTIPLIER, use_focus=False)
    calculations[TRANSPORT_NO_RISK] = calculate_profits_for_recipes(items.get_all_transport_recipes(),
                                                                    TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)


def update_crafting_calculations():
    global calculations
    calculations[CRAFTING_PER_CITY_NO_FOCUS] = calculate_local_per_city(items.get_all_crafting_recipes(),
                                                                        use_focus=False)
    calculations[CRAFTING_PER_CITY_WITH_FOCUS] = calculate_local_per_city(items.get_all_crafting_recipes(),
                                                                          use_focus=True)
    calculations[CRAFTING_NO_TRAVEL_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                              NO_TRAVEL_MULTIPLIER, use_focus=False)
    calculations[CRAFTING_NO_TRAVEL_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                                NO_TRAVEL_MULTIPLIER, use_focus=True)
    calculations[CRAFTING_NO_RISK_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                            TRAVEL_COST_NO_RISK_MULTIPLIER,
                                                                            use_focus=False)
    calculations[CRAFTING_NO_RISK_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                              TRAVEL_COST_NO_RISK_MULTIPLIER,
                                                                              use_focus=True)
    calculations[CRAFTING_TRAVEL_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                           TRAVEL_COST_MULTIPLIER, use_focus=False)
    calculations[CRAFTING_TRAVEL_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                             TRAVEL_COST_MULTIPLIER, use_focus=True)


def calculate_local_per_city(recipes, use_focus):
    return {city_name: calculate_profits_for_recipes(recipes, multiplier, use_focus)
            for city_name, multiplier in zip(cities.cities_names(), ONE_CITY_ONLY_MULTIPLIERS)}


def calculate_profits_for_recipes(recipes, multiplier, use_focus):
    return [calculate_profit_details_for_recipe(recipe, multiplier, use_focus) for recipe in recipes]


if __name__ == '__main__':
    result = [calculate_profit_details_for_recipe(recipe, TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)
              for recipe in tqdm.tqdm(items.get_all_recipes(), desc='calculating profit')]

    print('end')
