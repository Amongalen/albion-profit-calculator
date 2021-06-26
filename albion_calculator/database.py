import logging

from sqlalchemy import desc

from albion_calculator.models import CalculationsUpdate


def save_calculations_update(calculations_update: CalculationsUpdate):
    from albion_calculator.webapp import db
    db.session.add(calculations_update)
    db.session.commit()
    logging.debug(f'{len(calculations_update.profit_details)} calculations saved to DB')


def clear_previous_calculation_updates():
    from albion_calculator.webapp import db
    latest_calculation_update = db.session.query(CalculationsUpdate.id).order_by(desc(CalculationsUpdate.id)).first()
    db.session.query(CalculationsUpdate).filter(CalculationsUpdate.id != latest_calculation_update.id).delete()
    db.session.commit()
    logging.debug('old calculations removed')
