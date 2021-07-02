from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, registry

from albion_calculator_backend.models import RecipeType

mapper_registry = registry()


@mapper_registry.mapped
@dataclass
class IngredientDetails:
    __tablename__ = 'ingredient_details'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(
        init=False, metadata={"sa": Column(Integer, primary_key=True)})
    item_name: str = field(default=None, metadata={"sa": Column(String(100))})
    item_id: str = field(default=None, metadata={"sa": Column(String(100))})
    quantity: int = field(default=None, metadata={"sa": Column(Integer)})
    local_price: float = field(default=None, metadata={"sa": Column(Float)})
    total_cost: float = field(default=None, metadata={"sa": Column(Float)})
    total_cost_with_transport: float = field(default=None, metadata={"sa": Column(Float)})
    total_cost_with_returns: float = field(default=None, metadata={"sa": Column(Float)})
    source_city: str = field(default=None, metadata={"sa": Column(String(100))})
    profit_details_id: int = field(default=None, metadata={
        "sa": Column(Integer, ForeignKey('profit_details.id', ondelete="CASCADE"))})


@mapper_registry.mapped
@dataclass
class ProfitDetails:
    __tablename__ = 'profit_details'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(
        init=False, metadata={"sa": Column(Integer, primary_key=True)})
    product_id: str = field(default=None, metadata={"sa": Column(String(100))})
    product_name: str = field(default=None, metadata={"sa": Column(String(100))})
    product_subcategory: str = field(default=None, metadata={"sa": Column(String(100))})
    product_subcategory_id: str = field(default=None, metadata={"sa": Column(String(100))})
    product_tier: str = field(default=None, metadata={"sa": Column(String(100))})
    product_quantity: int = field(default=None, metadata={"sa": Column(Integer)})
    recipe_type: RecipeType = field(default=None, metadata={"sa": Column(String(100))})
    final_product_price: float = field(default=None, metadata={"sa": Column(Float)})
    ingredients_total_cost: float = field(default=None, metadata={"sa": Column(Float)})
    profit_without_journals: float = field(default=None, metadata={"sa": Column(Float)})
    profit_per_journal: float = field(default=None, metadata={"sa": Column(Float)})
    journals_filled: float = field(default=None, metadata={"sa": Column(Float)})
    profit_with_journals: float = field(default=None, metadata={"sa": Column(Float)})
    profit_percentage: float = field(default=None, metadata={"sa": Column(Float)})
    destination_city: str = field(default=None, metadata={"sa": Column(String(100))})
    production_city: str = field(default=None, metadata={"sa": Column(String(100))})
    ingredients_details: list[IngredientDetails] = field(default=None,
                                                         metadata={"sa": relationship(IngredientDetails,
                                                                                      cascade='all,delete-orphan',
                                                                                      passive_deletes=True,
                                                                                      lazy=False)})
    calculations_updates_id: int = field(default=None, metadata={
        "sa": Column(Integer, ForeignKey('calculations_updates.id', ondelete="CASCADE"))})


@mapper_registry.mapped
@dataclass
class CalculationsUpdate:
    __tablename__ = 'calculations_updates'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(
        init=False, metadata={"sa": Column(Integer, primary_key=True)})
    type_key: str = field(default=None, metadata={"sa": Column(String(100))})
    profit_details: list[ProfitDetails] = field(default=None,
                                                metadata={"sa": relationship(ProfitDetails,
                                                                             cascade='all,delete-orphan',
                                                                             backref='calculations_updates',
                                                                             passive_deletes=True,
                                                                             lazy=True)})
    update_time: datetime = field(default=None, metadata={"sa": Column(DateTime, default=datetime.now)})
