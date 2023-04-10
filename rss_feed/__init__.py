import os

import click
from flask import Flask
from flask.cli import with_appcontext

from rss_feed.models import db


def create_app(test_config=None):
    # create and configure the app
    BASE_URL = '/rss-feed' if os.environ['FLASK_ENV'] == 'production' else ''
    app = Flask(__name__, instance_relative_config=True, static_url_path=f'{BASE_URL}/static')
    app.config.from_mapping(SECRET_KEY='dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config["SQLALCHEMY_ECHO"] = True
    app.
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config that was passed in
        app.config.from_mapping(test_config)
    # Ensure the app folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import auth
    app.register_blueprint(auth.bp)

    from . import rss_feed
    app.register_blueprint(rss_feed.bp)

    db.init_app(app)
    app.cli.add_command(init_db_command)

    return app

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.session.commit()
    db.create_all()
    db.session.commit()
    click.echo('Initialized the database.')
