import jinja2
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Blueprint, render_template, request, session, redirect, url_for

from albion_calculator import calculator, shop_categories, config

bp = Blueprint('webapp', __name__)


@bp.context_processor
def inject_categories() -> dict:
    categories = {category: shop_categories.get_category_pretty_name(category) for category in
                  shop_categories.get_craftable_shop_categories()}
    return dict(categories=categories)


@bp.context_processor
def inject_travel_multiplier() -> dict:
    return dict(one_tile_multiplier=calculator.ONE_TILE,
                two_tiles_multiplier=calculator.TWO_TILES)


@bp.route('/details', methods=['GET', 'POST'])
def show_details() -> str:
    calculation = request.json
    return render_template('details.html', calculation=calculation)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/results', methods=['POST', 'GET'])
def results():
    if request.method == 'POST':
        form_data = request.form
        session['formdata'] = form_data
    else:
        form_data = session.get('formdata', None)

    if not form_data:
        return redirect(url_for('webapp.index'))

    calculations, update_time = calculator.get_calculations(recipe_type=form_data.get('recipe_type', 'CRAFTING'),
                                                            limitation=form_data.get('limitation', 'TRAVEL'),
                                                            city_index=int(form_data.get('city', '0')),
                                                            use_focus=form_data.get('focus', False),
                                                            category=form_data.get('category', None))
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))
    page, paginated_calculations = paginate_calculations(calculations, page, page_size)
    return render_template('index.html', page=page, page_size=page_size,
                           calculations=paginated_calculations, update_time=update_time)


def paginate_calculations(calculations, page, page_size):
    start = (page - 1) * page_size
    end = page * page_size
    if start > len(calculations):
        page = len(calculations) // page_size
        start = page * page_size
    paginated_calculations = calculations[start:end]
    return page, paginated_calculations


def init() -> None:
    # calculator.initialize_or_update_calculations()
    _start_background_calculator_job()


def _start_background_calculator_job() -> None:
    scheduler = BackgroundScheduler(daemon=True)
    hours = config.CONFIG['APP']['WEBAPP']['UPDATE_HOURS']
    hours = hours if isinstance(hours, list) else [hours]
    scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour=','.join(hours))
    scheduler.start()


def datetime_format(value, format="%d-%m-%y %H:%M %Z"):
    return value.strftime(format)


jinja2.filters.FILTERS["datetime_format"] = datetime_format
