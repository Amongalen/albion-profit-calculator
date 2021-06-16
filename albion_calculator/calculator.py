import datetime
import logging
import time
from datetime import timedelta
from math import nan

import numpy as np
import tqdm

from albion_calculator import items, cities, journals, market, craftingmodifiers, shop_categories, config

from albion_calculator.items import Recipe
from albion_calculator.market import get_prices_for_item, get_price_for_item_in_city

_PROFIT_LIMIT = config.CONFIG['APP']['CALCULATOR']['PROFIT_PERCENTAGE_LIMIT']

_ONE_TILE = config.CONFIG['APP']['CALCULATOR']['TRAVEL_COST_ONE_TILE']

_TWO_TILE = _ONE_TILE ** 2


def _one_city_multipliers():
    arrays = []
    for i in range(6):
        array = np.empty((6, 6))
        array[:] = nan
        array[i][i] = 1
        arrays.append(array)
    return arrays


# MATRIX[transport_to][transport_from]
_MULTIPLIERS = {
    'TRAVEL': np.array([
        [1.0, _ONE_TILE, _TWO_TILE, _TWO_TILE, _ONE_TILE, _ONE_TILE],
        [_ONE_TILE, 1.0, _ONE_TILE, _TWO_TILE, _TWO_TILE, _ONE_TILE],
        [_TWO_TILE, _ONE_TILE, 1.0, _ONE_TILE, _TWO_TILE, _ONE_TILE],
        [_TWO_TILE, _TWO_TILE, _ONE_TILE, 1.0, _ONE_TILE, _ONE_TILE],
        [_ONE_TILE, _TWO_TILE, _TWO_TILE, _ONE_TILE, 1.0, _ONE_TILE],
        [_ONE_TILE, _ONE_TILE, _ONE_TILE, _ONE_TILE, _ONE_TILE, 1.0]
    ]),
    'NO_RISK': np.array([
        [1.0, _ONE_TILE, _TWO_TILE, _TWO_TILE, _ONE_TILE, nan],
        [_ONE_TILE, 1.0, _ONE_TILE, _TWO_TILE, _TWO_TILE, nan],
        [_TWO_TILE, _ONE_TILE, 1.0, _ONE_TILE, _TWO_TILE, nan],
        [_TWO_TILE, _TWO_TILE, _ONE_TILE, 1.0, _ONE_TILE, nan],
        [_ONE_TILE, _TWO_TILE, _TWO_TILE, _ONE_TILE, 1.0, nan],
        [nan, nan, nan, nan, nan, 1.0]
    ]),
    'NO_TRAVEL': np.array([
        [1.0, nan, nan, nan, nan, nan],
        [nan, 1.0, nan, nan, nan, nan],
        [nan, nan, 1.0, nan, nan, nan],
        [nan, nan, nan, 1.0, nan, nan],
        [nan, nan, nan, nan, 1.0, nan],
        [nan, nan, nan, nan, nan, 1.0]
    ]),
    'PER_CITY': _one_city_multipliers(),
}


def get_calculations(recipe_type, limitation, city_index, use_focus, category):
    key = _create_calculation_key(limitation, recipe_type, use_focus)
    city_name = cities.city_at_index(city_index)
    result = calculations[key][city_name] if limitation == 'PER_CITY' else calculations[key]
    if category and not category == 'all':
        result = [record for record in result if record['product_subcategory_id'] == category]
    return result


def _calculate_profit_details_for_recipe(recipe, multiplier, use_focus):
    missing_ingredients = _check_missing_ingredients_prices(recipe, multiplier)
    if missing_ingredients:
        return None
    ingredients_best_deals = _calculate_ingredients_best_deals(multiplier, recipe, use_focus)

    final_profit_matrix = _calculate_final_profit_matrix(ingredients_best_deals, multiplier, recipe)
    if np.isnan(final_profit_matrix).all():
        return None

    journal_profit_details = _calculate_journal_profit(recipe)
    profit_summary = _summarize_profit(final_profit_matrix, ingredients_best_deals, journal_profit_details, multiplier,
                                       recipe)
    return profit_summary


def _check_missing_ingredients_prices(recipe, multiplier):
    return [ingredient.item_id for ingredient in recipe.ingredients
            if np.isnan(market.get_prices_for_item(ingredient.item_id) * multiplier).all()]


def _summarize_profit(final_profit_matrix, ingredients_costs, journal_profit_details, multiplier, recipe):
    max_profit = np.nanmax(final_profit_matrix)
    final_profit = max_profit + journal_profit_details['journals_profit']
    destination_city_index, production_city_index = np.unravel_index(np.nanargmax(final_profit_matrix),
                                                                     final_profit_matrix.shape)
    ingredients_details = _summarize_ingredient_details(ingredients_costs, multiplier, production_city_index, recipe)
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
        'recipe_type': recipe.recipe_type,
        'profit_without_journals': round(max_profit, 2),
        'profit_with_journals': round(final_profit, 2),
        'profit_per_journal': round(journal_profit_details['profit_per_journal'], 2),
        'profit_percentage': round(final_profit / ingredients_total_cost * 100, 2),
        'journals_filled': round(journal_profit_details['journals_filled'], 2),
        'destination_city': cities.city_at_index(destination_city_index),
        'production_city': cities.city_at_index(production_city_index),
        'final_product_price': round(final_product_price, 2),
        'ingredients_details': ingredients_details,
        'ingredients_total_cost': ingredients_total_cost
    }
    return max_profit_details


def _summarize_ingredient_details(ingredients_costs, multiplier, production_city_index, recipe):
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
            'ingredient_id': item_id,
            'local_price': round(local_price, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_with_transport': round(total_cost_with_transport, 2),
            'total_cost_with_returns': round(price_with_returns, 2),
            'source_city': cities.city_at_index(import_from),
            'quantity': quantity
        })
    return ingredients_details


def _calculate_journal_profit(recipe):
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


def _find_ingredients_best_deals_per_city(ingredients_price_matrices):
    return [{item_id: _find_ingredient_best_deal_for_city(city, price_matrix)
             for item_id, price_matrix in ingredients_price_matrices.items()}
            for city in range(6)]


def _find_ingredient_best_deal_for_city(city, price_matrix):
    if np.isnan(price_matrix[city]).all():
        return nan, nan
    index = np.nanargmin(price_matrix[city])
    return price_matrix[city][index], index


def _calculate_final_profit_matrix(ingredients_costs, multiplier, recipe):
    ingredients_costs_total = [sum(item[0] for item in city.values()) for city in ingredients_costs]
    product_price = get_prices_for_item(recipe.result_item_id)
    return (product_price * recipe.result_quantity / multiplier).T - ingredients_costs_total


def _calculate_ingredients_best_deals(multiplier, recipe, use_focus):
    return_rates = craftingmodifiers.get_return_rates_vector(recipe.result_item_id, use_focus)
    ingredients_price_matrices = {
        ingredient.item_id: _calculate_single_ingredient_cost(ingredient, multiplier, recipe.recipe_type, return_rates)
        for ingredient in recipe.ingredients}
    ingredients_best_deals = _find_ingredients_best_deals_per_city(ingredients_price_matrices)
    return ingredients_best_deals


def _calculate_single_ingredient_cost(ingredient, multiplier, recipe_type, return_rates):
    price_matrix = get_prices_for_item(ingredient.item_id) * ingredient.quantity * multiplier
    if recipe_type == Recipe.CRAFTING_RECIPE and ingredient.max_return_rate != 0:
        price_matrix = price_matrix * return_rates
    return price_matrix


calculations = {}


def initialize_or_update_calculations():
    market.update_prices()
    _update_crafting_calculations()
    _update_transport_calculations()
    _update_upgrade_calculations()
    logging.info('all calculations loaded')


def _update_upgrade_calculations():
    global calculations
    recipes = items.get_all_upgrade_recipes()
    calculations.update(_calculate_profits('UPGRADE', 'PER_CITY', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'NO_TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'NO_RISK', recipes, use_focus=False))


def _update_transport_calculations():
    global calculations
    recipes = items.get_all_transport_recipes()
    calculations.update(_calculate_profits('TRANSPORT', 'TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('TRANSPORT', 'NO_RISK', recipes, use_focus=False))


def _update_crafting_calculations():
    global calculations
    recipes = items.get_all_crafting_recipes()
    calculations.update(_calculate_profits('CRAFTING', 'PER_CITY', recipes, use_focus=True))
    calculations.update(_calculate_profits('CRAFTING', 'PER_CITY', recipes, use_focus=False))
    calculations.update(_calculate_profits('CRAFTING', 'NO_TRAVEL', recipes, use_focus=True))
    calculations.update(_calculate_profits('CRAFTING', 'NO_TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('CRAFTING', 'TRAVEL', recipes, use_focus=True))
    calculations.update(_calculate_profits('CRAFTING', 'TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('CRAFTING', 'NO_RISK', recipes, use_focus=True))
    calculations.update(_calculate_profits('CRAFTING', 'NO_RISK', recipes, use_focus=False))


def _calculate_profits(recipe_type, limitations, recipes, use_focus):
    if limitations == 'PER_CITY':
        profits = _calculate_profits_per_city(recipes, use_focus)
    else:
        profits = _calculate_profits_for_recipes(recipes, _MULTIPLIERS[limitations], use_focus)
    key = _create_calculation_key(limitations, recipe_type, use_focus)
    logging.debug(f'{key} loaded')
    return {key: profits}


def _calculate_profits_per_city(recipes, use_focus):
    return {city_name: _calculate_profits_for_recipes(recipes, multiplier, use_focus)
            for city_name, multiplier in zip(cities.cities_names(), _MULTIPLIERS['PER_CITY'])}


def _calculate_profits_for_recipes(recipes, multiplier, use_focus):
    result = [details for recipe in recipes if
              (details := _calculate_profit_details_for_recipe(recipe, multiplier, use_focus))
              and details['profit_percentage'] < _PROFIT_LIMIT]
    return sorted(result, key=lambda x: x['profit_percentage'], reverse=True)


def _create_calculation_key(limitations, recipe_type, use_focus):
    use_focus_str = 'WITH_FOCUS' if use_focus else 'NO_FOCUS'
    return f'{recipe_type}_{limitations}_{use_focus_str}'
