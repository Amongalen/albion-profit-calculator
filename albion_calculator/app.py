from apscheduler.schedulers.background import BackgroundScheduler

from albion_calculator import calculator

calculator.initialize_or_update_calculations()
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(calculator.initialize_or_update_calculations, 'cron', hour='6,18')
scheduler.start()
