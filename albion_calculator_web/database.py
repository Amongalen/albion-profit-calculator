from datetime import datetime
from typing import Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Query

from albion_calculator_backend.database_models import CalculationsUpdate, ProfitDetails


def find_calculations_for_key_and_category(key: str, category: str) -> Tuple[Query, datetime]:
    from albion_calculator_web.webapp import app
    calculation_update = app.session.query(CalculationsUpdate).filter_by(type_key=key) \
        .order_by(desc(CalculationsUpdate.update_time)).first()
    if category != 'all':
        profit_details = app.session.query(ProfitDetails) \
            .filter_by(calculations_updates_id=calculation_update.id, product_subcategory_id=category)
    else:
        profit_details = app.session.query(ProfitDetails) \
            .filter_by(calculations_updates_id=calculation_update.id)
    return profit_details, calculation_update.update_time
