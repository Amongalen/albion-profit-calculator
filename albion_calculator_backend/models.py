from dataclasses import dataclass, field
from enum import Enum


class RecipeType(str, Enum):
    CRAFTING = 'crafting'
    UPGRADE = 'upgrade'
    TRANSPORT = 'transport'


@dataclass(frozen=True)
class Ingredient:
    item_id: str
    quantity: int
    max_return_rate: int


@dataclass(frozen=True)
class Recipe:
    result_item_id: str
    recipe_type: RecipeType
    result_quantity: int = 1
    silver_cost: int = 0
    ingredients: list[Ingredient] = field(default_factory=list)


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    category: str
    subcategory: str
    base_item_id: str
    recipes: list[Recipe] = field(default_factory=list)
    crafting_fame: int = 0
    item_value: int = 0
