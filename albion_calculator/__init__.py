import logging
import os

from flask import Flask

# from albion_calculator import webapp

logging.basicConfig(filename='logs.log', format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)


# todo display details in popup
def create_app():
    logging.error(os.getcwd())
    # webapp.init()
    app = Flask(__name__, static_folder='resources/static', template_folder='resources/templates',
                instance_relative_config=True)
    app.config.from_pyfile('config.py', silent=True)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # app.register_blueprint(webapp.bp)

    app.secret_key = 'secret'

    return app
