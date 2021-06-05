import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Blueprint, render_template, request

from albion_calculator import calculator

bp = Blueprint('webapp', __name__)


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
    calculations = calculator.get_calculations(recipe_type, limitation, city, focus, low_confidence)
    return render_template('index.html', calculations=calculations)


def init():
    calculator.initialize_or_update_calculations()
    # start_background_calculator_job()
    pass


def start_background_calculator_job():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour='6,18')
    scheduler.start()
