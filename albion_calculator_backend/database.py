import logging
import os

from sqlalchemy import desc, create_engine
from sqlalchemy.orm import sessionmaker

from albion_calculator_backend import database_models
from albion_calculator_backend.database_models import CalculationsUpdate, ProfitDetails, IngredientDetails

SQLALCHEMY_DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URI")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()


class BackendSession:
    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def bulk_insert_calculations_update(self, calculations_update: CalculationsUpdate):
        _assign_ids(calculations_update, *self._get_next_ids())
        calculations_update_raw, ingredient_details_raw, profit_details_raw = _extract_raw_attributes(
            calculations_update)

        self.session.bulk_insert_mappings(
            CalculationsUpdate,
            calculations_update_raw
        )
        self.session.bulk_insert_mappings(
            ProfitDetails,
            profit_details_raw
        )
        self.session.bulk_insert_mappings(
            IngredientDetails,
            ingredient_details_raw
        )
        self.session.commit()
        logging.debug(f'{len(calculations_update.profit_details)} calculations saved to DB')

    def delete_previous_calculation_updates(self, type_key: str):
        latest_calculation_update = db.query(CalculationsUpdate.id) \
            .filter(CalculationsUpdate.type_key == type_key) \
            .order_by(desc(CalculationsUpdate.id)).first()
        if latest_calculation_update:
            self.session.query(CalculationsUpdate) \
                .filter(CalculationsUpdate.id != latest_calculation_update.id, CalculationsUpdate.type_key == type_key) \
                .delete()
            self.session.commit()
            logging.debug(f'Old calculations for key {type_key} removed')

    def _get_next_ids(self):
        calculation_update_row = self.session.query(CalculationsUpdate.id).order_by(desc(CalculationsUpdate.id)).first()
        calculation_update_id = calculation_update_row.id + 1 if calculation_update_row else 1
        profit_details_row = self.session.query(ProfitDetails.id).order_by(desc(ProfitDetails.id)).first()
        profit_details_id = profit_details_row.id + 1 if profit_details_row else 1
        ingredient_details_row = self.session.query(IngredientDetails.id).order_by(desc(IngredientDetails.id)).first()
        ingredient_details_id = ingredient_details_row.id + 1 if ingredient_details_row else 1
        return calculation_update_id, profit_details_id, ingredient_details_id


def _assign_ids(calculations_update, calculation_update_id, profit_details_id, ingredient_details_id):
    calculations_update.id = calculation_update_id
    for profit_details in calculations_update.profit_details:
        profit_details.id = profit_details_id
        profit_details.calculations_updates_id = calculation_update_id
        for ingredient_details in profit_details.ingredients_details:
            ingredient_details.id = ingredient_details_id
            ingredient_details.profit_details_id = profit_details_id
            ingredient_details_id += 1
        profit_details_id += 1


def _extract_raw_attributes(calculations_update):
    calculations_updates_columns = CalculationsUpdate.__table__.columns
    calculations_update_raw = [{c.name: getattr(calculations_update, c.name) for c in calculations_updates_columns}]
    profit_details_columns = ProfitDetails.__table__.columns
    profit_details_raw = [{c.name: getattr(profit_details, c.name) for c in profit_details_columns} for
                          profit_details in calculations_update.profit_details]
    ingredient_details_columns = IngredientDetails.__table__.columns
    ingredient_details_raw = [{c.name: getattr(ingredient_details, c.name) for c in ingredient_details_columns}
                              for profit_details in calculations_update.profit_details
                              for ingredient_details in profit_details.ingredients_details]
    return calculations_update_raw, ingredient_details_raw, profit_details_raw


def init_db():
    database_models.mapper_registry.metadata.create_all(bind=engine)


def drop_db():
    database_models.mapper_registry.metadata.drop_all(bind=engine)
