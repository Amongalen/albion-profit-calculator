import os

from flask import Flask

from albion_calculator import webapp


def create_app():
    app = Flask(__name__, template_folder='resources/templates', instance_relative_config=True)
    app.config.from_pyfile('config.py', silent=True)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    webapp.init()
    app.register_blueprint(webapp.bp)

    return app
