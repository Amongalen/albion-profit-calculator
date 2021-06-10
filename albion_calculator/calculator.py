import datetime
import logging
import time
from datetime import timedelta
from math import nan

import numpy as np
import tqdm

from albion_calculator import items, cities, journals, market, craftingmodifiers, shop_categories

from albion_calculator.items import Recipe
from albion_calculator.market import get_prices_for_item, get_price_for_item_in_city

NONE = nan

ONE_TILE = 1.05

TWO_TILE = ONE_TILE ** 2

BASE = 1.0

UPGRADE_TRAVEL = 'UPGRADE_TRAVEL'

UPGRADE_NO_RISK = 'UPGRADE_NO_RISK'

UPGRADE_NO_TRAVEL = 'UPGRADE_NO_TRAVEL'

UPGRADE_PER_CITY = 'UPGRADE_PER_CITY'

TRANSPORT_NO_RISK = 'TRANSPORT_NO_RISK'

TRANSPORT_TRAVEL = 'TRANSPORT_TRAVEL'

CRAFTING_NO_RISK_WITH_FOCUS = 'CRAFTING_NO_RISK_WITH_FOCUS'

CRAFTING_TRAVEL_NO_FOCUS = 'CRAFTING_TRAVEL_NO_FOCUS'

CRAFTING_TRAVEL_WITH_FOCUS = 'CRAFTING_TRAVEL_WITH_FOCUS'

CRAFTING_NO_RISK_NO_FOCUS = 'CRAFTING_NO_RISK_NO_FOCUS'

CRAFTING_NO_TRAVEL_WITH_FOCUS = 'CRAFTING_NO_TRAVEL_WITH_FOCUS'

CRAFTING_PER_CITY_WITH_FOCUS = 'CRAFTING_PER_CITY_WITH_FOCUS'

CRAFTING_PER_CITY_NO_FOCUS = 'CRAFTING_PER_CITY_NO_FOCUS'

CRAFTING_NO_TRAVEL_NO_FOCUS = 'CRAFTING_NO_TRAVEL_NO_FOCUS'

LOW_CONFIDENCE_THRESHOLD = 20

# MATRIX[transport_to][transport_from]
TRAVEL_COST_MULTIPLIER = np.array([
    [BASE, ONE_TILE, TWO_TILE, TWO_TILE, ONE_TILE, ONE_TILE],
    [ONE_TILE, BASE, ONE_TILE, TWO_TILE, TWO_TILE, ONE_TILE],
    [TWO_TILE, ONE_TILE, BASE, ONE_TILE, TWO_TILE, ONE_TILE],
    [TWO_TILE, TWO_TILE, ONE_TILE, BASE, ONE_TILE, ONE_TILE],
    [ONE_TILE, TWO_TILE, TWO_TILE, ONE_TILE, BASE, ONE_TILE],
    [ONE_TILE, ONE_TILE, ONE_TILE, ONE_TILE, ONE_TILE, BASE]
])

TRAVEL_COST_NO_RISK_MULTIPLIER = np.array([
    [BASE, ONE_TILE, TWO_TILE, TWO_TILE, ONE_TILE, NONE],
    [ONE_TILE, BASE, ONE_TILE, TWO_TILE, TWO_TILE, NONE],
    [TWO_TILE, ONE_TILE, BASE, ONE_TILE, TWO_TILE, NONE],
    [TWO_TILE, TWO_TILE, ONE_TILE, BASE, ONE_TILE, NONE],
    [ONE_TILE, TWO_TILE, TWO_TILE, ONE_TILE, BASE, NONE],
    [NONE, NONE, NONE, NONE, NONE, BASE]
])

NO_TRAVEL_MULTIPLIER = np.array([
    [BASE, NONE, NONE, NONE, NONE, NONE],
    [NONE, BASE, NONE, NONE, NONE, NONE],
    [NONE, NONE, BASE, NONE, NONE, NONE],
    [NONE, NONE, NONE, BASE, NONE, NONE],
    [NONE, NONE, NONE, NONE, BASE, NONE],
    [NONE, NONE, NONE, NONE, NONE, BASE]
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


def get_calculations(recipe_type, limitation, city_index, focus, low_confidence, category):
    focus_str = 'WITH_FOCUS' if focus else 'NO_FOCUS'
    index = f'{recipe_type}_{limitation}_{focus_str}' if recipe_type == 'CRAFTING' else f'{recipe_type}_{limitation}'
    city_name = cities.city_at_index(city_index)
    result = calculations[index][city_name] if limitation == 'PER_CITY' else calculations[index]
    if category and not category == 'all':
        result = [record for record in result if record['product_subcategory_id'] == category]
    return result if low_confidence else filter_out_low_confidence(result)


def filter_out_low_confidence(lst):
    return [record for record in lst if record['amount_sold'] >= LOW_CONFIDENCE_THRESHOLD and
            all(ingredient['amount_sold'] >= LOW_CONFIDENCE_THRESHOLD for ingredient in
                record['ingredients_details'])]


def check_missing_ingredients_prices(recipe, multiplier):
    return [ingredient.item_id for ingredient in recipe.ingredients
            if np.isnan(market.get_prices_for_item(ingredient.item_id) * multiplier).all()]


def calculate_profit_details_for_recipe(recipe, multiplier, use_focus):
    missing_ingredients = check_missing_ingredients_prices(recipe, multiplier)
    if missing_ingredients:
        return {'missing_item_price': missing_ingredients}
    ingredients_best_deals = calculate_ingredients_best_deals(multiplier, recipe, use_focus)

    final_profit_matrix = calculate_final_profit_matrix(ingredients_best_deals, multiplier, recipe)
    if np.isnan(final_profit_matrix).all():
        return {'missing_item_price': recipe.result_item_id}

    journal_profit_details = calculate_journal_profit(recipe)
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
        'product_name': items.get_item_name(recipe.result_item_id),
        'product_id': recipe.result_item_id,
        'product_subcategory': shop_categories.get_category_pretty_name(
            items.get_item_subcategory(recipe.result_item_id)),
        'product_subcategory_id': items.get_item_subcategory(recipe.result_item_id),
        'product_tier': items.get_item_tier(recipe.result_item_id),
        'product_quantity': recipe.result_quantity,
        'profit_without_journals': round(max_profit, 2),
        'profit_with_journals': round(final_profit, 2),
        'profit_per_journal': round(journal_profit_details['profit_per_journal'], 2),
        'profit_percentage': round(final_profit / ingredients_total_cost * 100, 2),
        'journals_filled': round(journal_profit_details['journals_filled'], 2),
        'destination_city': cities.city_at_index(destination_city_index),
        'production_city': cities.city_at_index(production_city_index),
        'final_product_price': round(final_product_price, 2),
        'ingredients_details': ingredients_details,
        'ingredients_total_cost': ingredients_total_cost,
        'amount_sold': market.get_amount_sold(recipe.result_item_id, production_city_index)
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
            'ingredient_name': items.get_item_name(item_id),
            'local_price': round(local_price, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_with_transport': round(total_cost_with_transport, 2),
            'total_cost_with_returns': round(price_with_returns, 2),
            'source_city': cities.city_at_index(import_from),
            'quantity': quantity,
            'amount_sold': market.get_amount_sold(item_id, import_from)
        })
    return ingredients_details


def calculate_journal_profit(recipe):
    no_journal_profit = {'journals_profit': 0, 'profit_per_journal': 0, 'journals_filled': 0}
    if not recipe.recipe_type == Recipe.CRAFTING_RECIPE:
        return no_journal_profit
    item_id = recipe.result_item_id
    journal = journals.get_journal_for_item(item_id)
    if journal is None:
        return no_journal_profit
    crafting_fame = items.get_item_crafting_fame(item_id)
    full_journal_price = market.get_avg_price_for_item(journal['item_id'] + '_FULL')
    empty_journal_price = journal['cost']
    if np.isnan(full_journal_price) or empty_journal_price == 0:
        return no_journal_profit
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
    market.update_prices()
    # update_crafting_calculations()
    update_transport_calculations()
    # update_upgrade_calculations()
    logging.info('all calculations loaded')


def update_upgrade_calculations():
    global calculations
    calculations[UPGRADE_PER_CITY] = calculate_local_per_city(items.get_all_upgrade_recipes(), use_focus=False)
    logging.debug(f'{UPGRADE_PER_CITY} loaded')
    calculations[UPGRADE_NO_TRAVEL] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                    NO_TRAVEL_MULTIPLIER, use_focus=False)
    logging.debug(f'{UPGRADE_NO_TRAVEL} loaded')
    calculations[UPGRADE_NO_RISK] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                  TRAVEL_COST_NO_RISK_MULTIPLIER, use_focus=False)
    logging.debug(f'{UPGRADE_NO_RISK} loaded')
    calculations[UPGRADE_TRAVEL] = calculate_profits_for_recipes(items.get_all_upgrade_recipes(),
                                                                 TRAVEL_COST_MULTIPLIER, use_focus=False)
    logging.debug(f'{UPGRADE_TRAVEL} loaded')


def update_transport_calculations():
    global calculations
    calculations[TRANSPORT_TRAVEL] = calculate_profits_for_recipes(items.get_all_transport_recipes(),
                                                                   TRAVEL_COST_MULTIPLIER, use_focus=False)
    logging.debug(f'{TRANSPORT_TRAVEL} loaded')
    calculations[TRANSPORT_NO_RISK] = calculate_profits_for_recipes(items.get_all_transport_recipes(),
                                                                    TRAVEL_COST_NO_RISK_MULTIPLIER,
                                                                    use_focus=False)
    logging.debug(f'{TRANSPORT_NO_RISK} loaded')


def update_crafting_calculations():
    global calculations
    calculations[CRAFTING_PER_CITY_NO_FOCUS] = calculate_local_per_city(items.get_all_crafting_recipes(),
                                                                        use_focus=False)
    logging.debug(f'{CRAFTING_PER_CITY_NO_FOCUS} loaded')
    calculations[CRAFTING_PER_CITY_WITH_FOCUS] = calculate_local_per_city(items.get_all_crafting_recipes(),
                                                                          use_focus=True)
    logging.debug(f'{CRAFTING_PER_CITY_WITH_FOCUS} loaded')
    calculations[CRAFTING_NO_TRAVEL_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                              NO_TRAVEL_MULTIPLIER, use_focus=False)
    logging.debug(f'{CRAFTING_NO_TRAVEL_NO_FOCUS} loaded')
    calculations[CRAFTING_NO_TRAVEL_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                                NO_TRAVEL_MULTIPLIER, use_focus=True)
    logging.debug(f'{CRAFTING_NO_TRAVEL_WITH_FOCUS} loaded')
    calculations[CRAFTING_NO_RISK_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                            TRAVEL_COST_NO_RISK_MULTIPLIER,
                                                                            use_focus=False)
    logging.debug(f'{CRAFTING_NO_RISK_NO_FOCUS} loaded')
    calculations[CRAFTING_NO_RISK_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                              TRAVEL_COST_NO_RISK_MULTIPLIER,
                                                                              use_focus=True)
    logging.debug(f'{CRAFTING_NO_RISK_WITH_FOCUS} loaded')
    calculations[CRAFTING_TRAVEL_NO_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                           TRAVEL_COST_MULTIPLIER, use_focus=False)
    logging.debug(f'{CRAFTING_TRAVEL_NO_FOCUS} loaded')
    calculations[CRAFTING_TRAVEL_WITH_FOCUS] = calculate_profits_for_recipes(items.get_all_crafting_recipes(),
                                                                             TRAVEL_COST_MULTIPLIER, use_focus=True)
    logging.debug(f'{CRAFTING_TRAVEL_WITH_FOCUS} loaded')


def calculate_local_per_city(recipes, use_focus):
    return {city_name: calculate_profits_for_recipes(recipes, multiplier, use_focus)
            for city_name, multiplier in zip(cities.cities_names(), ONE_CITY_ONLY_MULTIPLIERS)}


def calculate_profits_for_recipes(recipes, multiplier, use_focus):
    result = []
    for recipe in recipes:
        details = calculate_profit_details_for_recipe(recipe, multiplier, use_focus)
        if 'missing_item_price' not in details:
            result.append(details)
    return sorted(result, key=lambda x: x['profit_percentage'], reverse=True)
