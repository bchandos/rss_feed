import os

import click
from flask import Flask
from flask.cli import with_appcontext

from rss_feed.models import db, User, UserFeed, Feed

from werkzeug.security import generate_password_hash

def create_app(test_config=None):
    # create and configure the app
    BASE_URL = '/rss-feed' if os.environ['FLASK_ENV'] == 'production' else ''
    app = Flask(__name__, instance_relative_config=True, static_url_path=f'{BASE_URL}/static')
    app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config["SQLALCHEMY_ECHO"] = True
    
    # Cookie settings
    app.config['SESSION_COOKIE_NAME'] = 'rss_feed_session'
    if BASE_URL:
        app.config['SESSION_COOKIE_PATH'] = BASE_URL
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800
    
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
    
    with app.app_context():
        try:
            if os.environ.get('DEMO_MODE', False) == 'true':
                demo_mode_setup()
            db.create_all()
            db.session.commit()
        except:
            raise

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

def demo_mode_setup():
    db.drop_all()
    db.session.commit()
    db.create_all()
    db.session.commit()
    # Create a demo user
    new_user = User(username='demo', password=generate_password_hash('demo'))
    db.session.add(new_user)
    db.session.commit()
    # Add two example feeds
    feed_1 = Feed(
        name='Biz & IT – Ars Technica',
        url='https://feeds.arstechnica.com/arstechnica/technology-lab'
    )
    feed_2 = Feed(
        name='www.espn.com - TOP',
        url='https://www.espn.com/espn/rss/news'
    )
    db.session.add(feed_1)
    db.session.add(feed_2)
    db.session.commit()
    user_feed_1 = UserFeed(
        user_id=new_user.id,
        feed_id=feed_1.id
    )
    user_feed_2 = UserFeed(
        user_id=new_user.id,
        feed_id=feed_2.id
    )
    db.session.add(user_feed_1)
    db.session.add(user_feed_2)
    # Commit it!
    db.session.commit()
