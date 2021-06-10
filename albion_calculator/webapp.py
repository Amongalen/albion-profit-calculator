import datetime
import json

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Blueprint, render_template, request

from albion_calculator import calculator, craftingmodifiers, shop_categories

bp = Blueprint('webapp', __name__)


@bp.context_processor
def inject_categories():
    categories = {category: shop_categories.get_category_pretty_name(category) for category in
                  shop_categories.get_craftable_shop_categories()}
    return dict(categories=categories)


@bp.route('/details', methods=['GET', 'POST'])
def show_details():
    calculation = request.json
    return render_template('details.html', calculation=calculation)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/', methods=['POST'])
def show_calculations():
    recipe_type = request.form.get('recipe_type', 'CRAFTING')
    limitation = request.form.get('limitation', 'TRAVEL')
    city = int(request.form.get('city', '0'))
    focus = request.form.get('focus', False)
    low_confidence = request.form.get('low_confidence', False)
    category = request.form.get('category', None)
    calculations = calculator.get_calculations(recipe_type, limitation, city, focus, low_confidence, category)
    return render_template('index.html', calculations=calculations)


def init():
    calculator.initialize_or_update_calculations()
    # start_background_calculator_job()
    pass


def start_background_calculator_job():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour='6,18')
    scheduler.start()
