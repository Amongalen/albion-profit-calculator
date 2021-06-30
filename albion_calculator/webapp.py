import logging
import os

import jinja2
from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, request, session, redirect, url_for, Flask
from flask_sqlalchemy import SQLAlchemy

from albion_calculator import calculator, shop_categories, config, models

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)


def create_app():
    app = Flask(__name__, static_folder='resources/static', template_folder='resources/templates',
                instance_relative_config=True)
    app.config.from_pyfile('config.py', silent=True)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app


def start_background_calculator_job() -> None:
    scheduler = BackgroundScheduler(daemon=True)
    hours = config.CONFIG['APP']['WEBAPP']['UPDATE_HOURS']
    hours = hours if isinstance(hours, list) else [hours]
    hours = [str(hour) for hour in hours]
    scheduler.add_job(calculator.update_calculations)
    scheduler.add_job(calculator.update_calculations, 'cron', hour=','.join(hours))
    scheduler.start()


app = create_app()
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
db = SQLAlchemy(app)
models.init_db()
if os.environ.get("INIT_APP", True) != 'False':
    start_background_calculator_job()


@app.context_processor
def inject_categories() -> dict:
    categories = {category: shop_categories.get_category_pretty_name(category) for category in
                  shop_categories.get_craftable_shop_categories()}
    return dict(categories=categories)


@app.context_processor
def inject_travel_multiplier() -> dict:
    return dict(one_tile_multiplier=calculator.ONE_TILE,
                two_tiles_multiplier=calculator.TWO_TILES)


@app.route('/details', methods=['GET', 'POST'])
def show_details() -> str:
    calculation = request.json
    return render_template('details.html', calculation=calculation)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/results', methods=['POST', 'GET'])
def results():
    if request.method == 'POST':
        form_data = request.form
        session['formdata'] = form_data
    else:
        form_data = session.get('formdata', None)

    if not form_data:
        return redirect(url_for('index'))
    calculations, update_time = calculator.get_calculations(recipe_type=form_data.get('recipe_type', 'CRAFTING'),
                                                            limitation=form_data.get('limitation', 'TRAVEL'),
                                                            city_index=int(form_data.get('city', '0')),
                                                            use_focus=form_data.get('focus', False),
                                                            category=form_data.get('category', None))
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    return render_template('index.html', page=page, per_page=per_page,
                           calculations=calculations, update_time=update_time)


def paginate_calculations(calculations, page, page_size):
    start = (page - 1) * page_size
    end = page * page_size
    if start > len(calculations):
        page = len(calculations) // page_size
        start = page * page_size
    paginated_calculations = calculations[start:end]
    return page, paginated_calculations


def datetime_format(value, format="%d-%m-%y %H:%M %Z"):
    return value.strftime(format)


jinja2.filters.FILTERS["datetime_format"] = datetime_format
