import logging
from datetime import datetime
from typing import Tuple

from flask_sqlalchemy import Pagination
from sqlalchemy import desc

from albion_calculator.models import CalculationsUpdate, ProfitDetails, IngredientDetails


def bulk_insert_calculations_update(calculations_update: CalculationsUpdate):
    from albion_calculator.webapp import db
    _assign_ids(calculations_update)
    calculations_update_raw, ingredient_details_raw, profit_details_raw = _extract_raw_attributes(calculations_update)
    db.session.bulk_insert_mappings(
        CalculationsUpdate,
        calculations_update_raw
    )
    db.session.bulk_insert_mappings(
        ProfitDetails,
        profit_details_raw
    )
    db.session.bulk_insert_mappings(
        IngredientDetails,
        ingredient_details_raw
    )
    db.session.commit()
    logging.debug(f'{len(calculations_update.profit_details)} calculations saved to DB')


def delete_previous_calculation_updates(type_key: str):
    from albion_calculator.webapp import db
    latest_calculation_update = db.session.query(CalculationsUpdate.id) \
        .filter(CalculationsUpdate.type_key == type_key) \
        .order_by(desc(CalculationsUpdate.id)).first()
    db.session.query(CalculationsUpdate) \
        .filter(CalculationsUpdate.id != latest_calculation_update.id, CalculationsUpdate.type_key == type_key) \
        .delete()
    db.session.commit()
    logging.debug('Old calculations removed')


def find_calculations_for_key_and_category(key: str, category: str) -> \
        Tuple[Pagination, datetime]:
    from albion_calculator.webapp import db
    calculation_update = db.session.query(CalculationsUpdate).order_by(desc(CalculationsUpdate.update_time)).first()
    if category != 'all':
        profit_details = db.session.query(ProfitDetails) \
            .filter_by(calculations_updates_id=calculation_update.id, type_key=key, product_subcategory_id=category) \
            .paginate(max_per_page=100)
    else:
        profit_details = db.session.query(ProfitDetails) \
            .filter_by(calculations_updates_id=calculation_update.id, type_key=key) \
            .paginate(max_per_page=100)
    return profit_details, calculation_update.update_time


def _extract_raw_attributes(calculations_update):
    from albion_calculator.webapp import db
    calculations_updates_columns = db.Table('calculations_updates', db.metadata, autoload=True).columns
    calculations_update_raw = [{c.name: getattr(calculations_update, c.name) for c in calculations_updates_columns}]
    profit_details_columns = db.Table('profit_details', db.metadata, autoload=True).columns
    profit_details_raw = [{c.name: getattr(profit_details, c.name) for c in profit_details_columns} for
                          profit_details in calculations_update.profit_details]
    ingredient_details_columns = db.Table('ingredient_details', db.metadata, autoload=True).columns
    ingredient_details_raw = [{c.name: getattr(ingredient_details, c.name) for c in ingredient_details_columns}
                              for profit_details in calculations_update.profit_details
                              for ingredient_details in profit_details.ingredients_details]
    return calculations_update_raw, ingredient_details_raw, profit_details_raw


def _assign_ids(calculations_update):
    calculation_update_id, profit_details_id, ingredient_details_id = _get_next_ids()
    calculations_update.id = calculation_update_id
    for profit_details in calculations_update.profit_details:
        profit_details.id = profit_details_id
        profit_details.calculations_updates_id = calculation_update_id
        for ingredient_details in profit_details.ingredients_details:
            ingredient_details.id = ingredient_details_id
            ingredient_details.profit_details_id = profit_details_id
            ingredient_details_id += 1
        profit_details_id += 1


def _get_next_ids():
    from albion_calculator.webapp import db
    calculation_update_row = db.session.query(CalculationsUpdate.id).order_by(desc(CalculationsUpdate.id)).first()
    calculation_update_id = calculation_update_row.id + 1 if calculation_update_row else 1
    profit_details_row = db.session.query(ProfitDetails.id).order_by(desc(ProfitDetails.id)).first()
    profit_details_id = profit_details_row.id + 1 if profit_details_row else 1
    ingredient_details_row = db.session.query(IngredientDetails.id).order_by(desc(IngredientDetails.id)).first()
    ingredient_details_id = ingredient_details_row.id + 1 if ingredient_details_row else 1
    return calculation_update_id, profit_details_id, ingredient_details_id
