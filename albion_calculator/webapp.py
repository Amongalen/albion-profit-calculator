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
    form = request.form
    return render_template('index.html')


def init():
    # calculator.initialize_or_update_calculations()
    # start_background_calculator_job()
    pass


def start_background_calculator_job():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour='6,18')
    scheduler.start()


if __name__ == '__main__':
    init()
