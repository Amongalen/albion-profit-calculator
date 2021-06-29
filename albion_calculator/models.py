from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import mapper


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


@dataclass
class IngredientDetails:
    id: int = field(init=False)
    item_name: str
    item_id: str
    quantity: int
    local_price: float
    total_cost: float
    total_cost_with_transport: float
    total_cost_with_returns: float
    source_city: str


@dataclass
class ProfitDetails:
    id: int = field(init=False)
    product_id: str
    product_name: str
    product_subcategory: str
    product_subcategory_id: str
    product_tier: str
    product_quantity: int
    recipe_type: RecipeType
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
    type_key: str = ''


@dataclass
class CalculationsUpdate:
    id: int = field(init=False)
    profit_details: list[ProfitDetails] = field(default_factory=list)
    update_time: datetime = datetime.now()


def init_db():
    from albion_calculator.webapp import db
    profit_details_table = db.Table('profit_details',
                                    Column('id', Integer, primary_key=True),
                                    Column('product_id', String(100)),
                                    Column('product_name', String(100)),
                                    Column('product_subcategory', String(100)),
                                    Column('product_subcategory_id', String(100)),
                                    Column('product_tier', String(10)),
                                    Column('product_quantity', Integer),
                                    Column('recipe_type', String(100)),
                                    Column('final_product_price', Float),
                                    Column('ingredients_total_cost', Float),
                                    Column('profit_without_journals', Float),
                                    Column('profit_per_journal', Float),
                                    Column('journals_filled', Float),
                                    Column('profit_with_journals', Float),
                                    Column('profit_percentage', Float),
                                    Column('destination_city', String(100)),
                                    Column('production_city', String(100)),
                                    Column('type_key', String(100)),
                                    Column('calculations_updates_id',
                                           ForeignKey('calculations_updates.id', ondelete="CASCADE")),
                                    mysql_engine='InnoDB'
                                    )
    ingredient_details_table = db.Table('ingredient_details',
                                        Column('id', Integer, primary_key=True),
                                        Column('item_name', String(100)),
                                        Column('item_id', String(100)),
                                        Column('quantity', Integer),
                                        Column('local_price', Float),
                                        Column('total_cost', Float),
                                        Column('total_cost_with_transport', Float),
                                        Column('total_cost_with_returns', Float),
                                        Column('source_city', String(100)),
                                        Column('profit_details_id',
                                               ForeignKey('profit_details.id', ondelete="CASCADE")),
                                        mysql_engine='InnoDB')
    calculations_updates_table = db.Table('calculations_updates',
                                          Column('id', Integer, primary_key=True),
                                          Column('update_time', DateTime),
                                          mysql_engine='InnoDB')

    mapper(CalculationsUpdate, calculations_updates_table, properties={
        'profit_details': db.relationship(ProfitDetails,
                                          cascade='all,delete,delete-orphan',
                                          backref='calculations_updates',
                                          passive_deletes=True,
                                          lazy=True)})
    mapper(ProfitDetails, profit_details_table, properties={
        'ingredients_details': db.relationship(IngredientDetails,
                                               cascade='all,delete,delete-orphan',
                                               backref='profit_details',
                                               passive_deletes=True,
                                               lazy=False)})
    mapper(IngredientDetails, ingredient_details_table)
