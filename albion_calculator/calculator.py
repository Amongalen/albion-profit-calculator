import datetime
import logging
from dataclasses import dataclass
from math import nan
from typing import Union, Optional

import numpy as np
from numpy import ndarray

from albion_calculator import items, cities, journals, market, craftingmodifiers, shop_categories, config
from albion_calculator.items import Recipe, Ingredient
from albion_calculator.market import get_prices_for_item, get_price_for_item_in_city

_PROFIT_LIMIT = config.CONFIG['APP']['CALCULATOR']['PROFIT_PERCENTAGE_LIMIT']

ONE_TILE = config.CONFIG['APP']['CALCULATOR']['TRAVEL_COST_ONE_TILE']

TWO_TILES = ONE_TILE ** 2


def _one_city_multipliers() -> list[ndarray]:
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
        [1.0, ONE_TILE, TWO_TILES, TWO_TILES, ONE_TILE, ONE_TILE],
        [ONE_TILE, 1.0, ONE_TILE, TWO_TILES, TWO_TILES, ONE_TILE],
        [TWO_TILES, ONE_TILE, 1.0, ONE_TILE, TWO_TILES, ONE_TILE],
        [TWO_TILES, TWO_TILES, ONE_TILE, 1.0, ONE_TILE, ONE_TILE],
        [ONE_TILE, TWO_TILES, TWO_TILES, ONE_TILE, 1.0, ONE_TILE],
        [ONE_TILE, ONE_TILE, ONE_TILE, ONE_TILE, ONE_TILE, 1.0]
    ]),
    'NO_RISK': np.array([
        [1.0, ONE_TILE, TWO_TILES, TWO_TILES, ONE_TILE, nan],
        [ONE_TILE, 1.0, ONE_TILE, TWO_TILES, TWO_TILES, nan],
        [TWO_TILES, ONE_TILE, 1.0, ONE_TILE, TWO_TILES, nan],
        [TWO_TILES, TWO_TILES, ONE_TILE, 1.0, ONE_TILE, nan],
        [ONE_TILE, TWO_TILES, TWO_TILES, ONE_TILE, 1.0, nan],
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


@dataclass
class IngredientDetails:
    name: str
    item_id: str
    quantity: int
    local_price: float
    total_cost: float
    total_cost_with_transport: float
    total_cost_with_returns: float
    source_city: str


@dataclass
class ProfitDetails:
    product_id: str
    product_name: str
    product_subcategory: str
    product_subcategory_id: str
    product_tier: str
    product_quantity: int
    recipe_type: str
    final_product_price: float
    ingredients_total_cost: float
    profit_without_journals: float
    profit_per_journal: float
    journals_filled: float
    profit_with_journals: float
    profit_percentage: float
    destination_city: str
    production_city: str
    ingredients_details: list[IngredientDetails]


def get_calculations(recipe_type: str, limitation: str, city_index: int, use_focus: bool,
                     category: str) -> tuple[list[ProfitDetails], datetime]:
    key = _create_calculation_key(limitation, recipe_type, use_focus)
    city_name = cities.city_at_index(city_index)
    result = calculations[key][city_name] if limitation == 'PER_CITY' else calculations[key]
    if category and not category == 'all':
        result = [record for record in result if record.product_subcategory_id == category]
    return result, update_datetime


def _calculate_profit_details_for_recipe(recipe: Recipe, multiplier: ndarray,
                                         use_focus: bool) -> Optional[ProfitDetails]:
    missing_ingredients = _check_missing_ingredients_prices(recipe, multiplier)
    if missing_ingredients:
        return None
    ingredients_best_deals = _calculate_ingredients_best_deals(multiplier, recipe, use_focus)

    final_profit_matrix = _calculate_final_profit_matrix(ingredients_best_deals, multiplier, recipe)
    if np.isnan(final_profit_matrix).all():
        return None

    journal_profit_details = _calculate_journal_profit(recipe)
    profit_details = _summarize_profit(final_profit_matrix, ingredients_best_deals, journal_profit_details, multiplier,
                                       recipe)
    return profit_details


def _check_missing_ingredients_prices(recipe: Recipe, multiplier: ndarray) -> list[str]:
    return [ingredient.item_id for ingredient in recipe.ingredients
            if np.isnan(market.get_prices_for_item(ingredient.item_id) * multiplier).all()]


def _summarize_profit(final_profit_matrix: ndarray, ingredients_costs: list[dict[str, tuple]],
                      journal_profit_details: dict[str, float], multiplier: ndarray, recipe: Recipe) -> ProfitDetails:
    max_profit = float(np.nanmax(final_profit_matrix))
    final_profit = max_profit + journal_profit_details['journals_profit']
    destination_city_index, production_city_index = np.unravel_index(np.nanargmax(final_profit_matrix),
                                                                     final_profit_matrix.shape)
    ingredients_details = _summarize_ingredient_details(ingredients_costs, multiplier, production_city_index, recipe)
    final_product_price = get_price_for_item_in_city(recipe.result_item_id, destination_city_index)
    ingredients_total_cost = sum(ingredient.total_cost_with_returns for ingredient in ingredients_details)

    return ProfitDetails(
        product_id=recipe.result_item_id,
        product_name=items.get_item_name(recipe.result_item_id),
        product_subcategory=shop_categories.get_category_pretty_name(items.get_item_subcategory(recipe.result_item_id)),
        product_subcategory_id=items.get_item_subcategory(recipe.result_item_id),
        product_tier=items.get_item_tier(recipe.result_item_id),
        product_quantity=recipe.result_quantity,
        recipe_type=recipe.recipe_type,
        final_product_price=int(final_product_price),
        ingredients_total_cost=ingredients_total_cost,
        profit_without_journals=int(max_profit),
        profit_per_journal=round(journal_profit_details['profit_per_journal'], 2),
        journals_filled=round(journal_profit_details['journals_filled'], 2),
        profit_with_journals=int(final_profit),
        profit_percentage=round(final_profit / ingredients_total_cost * 100, 2),
        destination_city=cities.city_at_index(destination_city_index),
        production_city=cities.city_at_index(production_city_index),
        ingredients_details=ingredients_details

    )


def _summarize_ingredient_details(ingredients_costs: list[dict[str, tuple]], multiplier: ndarray,
                                  production_city_index: int, recipe: Recipe) -> list[IngredientDetails]:
    ingredients_details = []
    for ingredient in recipe.ingredients:
        item_id = ingredient.item_id
        price_with_returns, import_from = ingredients_costs[production_city_index][item_id]
        quantity = ingredient.quantity
        local_price = get_price_for_item_in_city(item_id, import_from)
        total_cost = quantity * local_price
        total_cost_with_transport = total_cost * multiplier[import_from][production_city_index]
        ingredients_details.append(IngredientDetails(
            name=items.get_item_name(item_id),
            item_id=item_id,
            local_price=int(local_price),
            total_cost=int(total_cost),
            total_cost_with_transport=int(total_cost_with_transport),
            total_cost_with_returns=int(price_with_returns),
            source_city=cities.city_at_index(import_from),
            quantity=quantity
        ))
    return ingredients_details


def _calculate_journal_profit(recipe: Recipe) -> dict[str, float]:
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


def _find_ingredients_best_deals_per_city(ingredients_price_matrices: dict[str, ndarray]) -> list[dict[str, tuple]]:
    return [{item_id: _find_ingredient_best_deal_for_city(city, price_matrix)
             for item_id, price_matrix in ingredients_price_matrices.items()}
            for city in range(6)]


def _find_ingredient_best_deal_for_city(city_index: int, price_matrix: ndarray) -> tuple:
    if np.isnan(price_matrix[city_index]).all():
        return nan, nan
    index = np.nanargmin(price_matrix[city_index])
    return price_matrix[city_index][index], index


def _calculate_final_profit_matrix(ingredients_costs: list[dict[str, tuple]], multiplier: ndarray,
                                   recipe: Recipe) -> ndarray:
    ingredients_costs_total = [sum(item[0] for item in city.values()) for city in ingredients_costs]
    product_price = get_prices_for_item(recipe.result_item_id)
    return (product_price * recipe.result_quantity / multiplier).T - ingredients_costs_total


def _calculate_ingredients_best_deals(multiplier: ndarray, recipe: Recipe,
                                      use_focus: bool) -> list[dict[str, tuple]]:
    return_rates = craftingmodifiers.get_return_rates_vector(recipe.result_item_id, use_focus)
    ingredients_price_matrices = {
        ingredient.item_id: _calculate_single_ingredient_cost(ingredient, multiplier, recipe.recipe_type,
                                                              return_rates)
        for ingredient in recipe.ingredients}
    ingredients_best_deals = _find_ingredients_best_deals_per_city(ingredients_price_matrices)
    return ingredients_best_deals


def _calculate_single_ingredient_cost(ingredient: Ingredient, multiplier: ndarray, recipe_type: str,
                                      return_rates: ndarray) -> ndarray:
    price_matrix = get_prices_for_item(ingredient.item_id) * ingredient.quantity * multiplier
    if recipe_type == Recipe.CRAFTING_RECIPE and ingredient.max_return_rate != 0:
        price_matrix = price_matrix * return_rates
    return price_matrix


calculations = {}
update_datetime = None


def initialize_or_update_calculations() -> None:
    global update_datetime
    market.update_prices()
    _update_transport_calculations()
    if not config.CONFIG['APP']['CALCULATOR'].get('TESTING', False):
        _update_crafting_calculations()
        _update_upgrade_calculations()
    update_datetime = datetime.datetime.now()
    logging.info('all calculations loaded')


def _update_upgrade_calculations() -> None:
    global calculations
    recipes = items.get_all_upgrade_recipes()
    calculations.update(_calculate_profits('UPGRADE', 'PER_CITY', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'NO_TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('UPGRADE', 'NO_RISK', recipes, use_focus=False))


def _update_transport_calculations() -> None:
    global calculations
    recipes = items.get_all_transport_recipes()
    calculations.update(_calculate_profits('TRANSPORT', 'TRAVEL', recipes, use_focus=False))
    calculations.update(_calculate_profits('TRANSPORT', 'NO_RISK', recipes, use_focus=False))


def _update_crafting_calculations() -> None:
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


def _calculate_profits(recipe_type: str, limitations: str, recipes: list[Recipe], use_focus: bool) -> \
        Union[dict[str, list[ProfitDetails]], dict[str, dict[str, ProfitDetails]]]:
    if limitations == 'PER_CITY':
        profits = _calculate_profits_per_city(recipes, use_focus)
    else:
        profits = _calculate_profits_for_recipes(recipes, _MULTIPLIERS[limitations], use_focus)
    key = _create_calculation_key(limitations, recipe_type, use_focus)
    logging.debug(f'{key} loaded')
    return {key: profits}


def _calculate_profits_per_city(recipes: list[Recipe], use_focus: bool) -> dict[str, list[ProfitDetails]]:
    return {city_name: _calculate_profits_for_recipes(recipes, multiplier, use_focus)
            for city_name, multiplier in zip(cities.cities_names(), _MULTIPLIERS['PER_CITY'])}


def _calculate_profits_for_recipes(recipes: list[Recipe], multiplier: ndarray, use_focus: bool) -> list[ProfitDetails]:
    result = [details for recipe in recipes if
              (details := _calculate_profit_details_for_recipe(recipe, multiplier, use_focus))
              and details.profit_percentage < _PROFIT_LIMIT]
    return sorted(result, key=lambda x: x.profit_percentage, reverse=True)


def _create_calculation_key(limitations: str, recipe_type: str, use_focus: bool) -> str:
    use_focus_str = 'WITH_FOCUS' if use_focus else 'NO_FOCUS'
    return f'{recipe_type}_{limitations}_{use_focus_str}'
