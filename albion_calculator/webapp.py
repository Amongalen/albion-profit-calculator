from apscheduler.schedulers.background import BackgroundScheduler
from flask import Blueprint, render_template, request

from albion_calculator import calculator, shop_categories

bp = Blueprint('webapp', __name__)


@bp.context_processor
def inject_categories() -> dict:
    categories = {category: shop_categories.get_category_pretty_name(category) for category in
                  shop_categories.get_craftable_shop_categories()}
    return dict(categories=categories)


@bp.route('/details', methods=['GET', 'POST'])
def show_details() -> str:
    calculation = request.json
    return render_template('details.html', calculation=calculation)


@bp.route('/')
def index() -> str:
    return render_template('index.html')


@bp.route('/', methods=['POST'])
def show_calculations() -> str:
    recipe_type = request.form.get('recipe_type', 'CRAFTING')
    limitation = request.form.get('limitation', 'TRAVEL')
    city = int(request.form.get('city', '0'))
    focus = request.form.get('focus', False)
    category = request.form.get('category', None)
    calculations = calculator.get_calculations(recipe_type, limitation, city, focus, category)
    return render_template('index.html', calculations=calculations)


def init() -> None:
    calculator.initialize_or_update_calculations()
    # start_background_calculator_job()


def _start_background_calculator_job() -> None:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour='6,18')
    scheduler.start()
