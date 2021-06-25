from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

Ingredient = NamedTuple('Ingredient', item_id=str, quantity=int, max_return_rate=int)


class RecipeType(str, Enum):
    CRAFTING = 'crafting'
    UPGRADE = 'upgrade'
    TRANSPORT = 'transport'


@dataclass(frozen=True)
class Recipe:
    result_item_id: str
    recipe_type: RecipeType
    result_quantity: int = 1
    silver_cost: int = 0
    ingredients: list[Ingredient] = field(default_factory=list)


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    subcategory: str
    base_item_id: str
    recipes: list[Recipe] = field(default_factory=list)
    crafting_fame: int = 0
    item_value: int = 0


def get_all_items_ids() -> list[str]:
    return sorted(list(_items_data.keys()))[:200]


def get_item_subcategory(item_id: str) -> str:
    return _items_data[item_id].subcategory


def get_item_tier(item_id: str) -> str:
    return item_id[:2]


def get_item_name(item_id: str) -> str:
    return _items_data[item_id].name


def get_item_crafting_fame(item_id: str) -> float:
    return _items_data[item_id].crafting_fame


def get_items_ids_for_category_or_subcategory(*args: str) -> list[str]:
    return [item_id for item_id, item in _items_data.items()
            if item.subcategory in args
            or item.category in args]


def init_items_data():
    from albion_calculator.items_parser import load_items
    return load_items()


_items_data = init_items_data()


def get_all_transport_recipes() -> list[Recipe]:
    return _transport_recipes


def get_all_upgrade_recipes() -> list[Recipe]:
    return _upgrade_recipes


def get_all_crafting_recipes() -> list[Recipe]:
    return _crafting_recipes


def _load_recipes() -> list[Recipe]:
    return [recipe for item in _items_data.values() for recipe in item.recipes]


_recipes = _load_recipes()

_crafting_recipes = [recipe for recipe in _recipes if recipe.recipe_type == RecipeType.CRAFTING]
_upgrade_recipes = [recipe for recipe in _recipes if recipe.recipe_type == RecipeType.UPGRADE]
_transport_recipes = [recipe for recipe in _recipes if recipe.recipe_type == RecipeType.TRANSPORT]
