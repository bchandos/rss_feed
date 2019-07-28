import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import abort

from rss_feed.models import User, UserFeed, db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif User.query.filter(User.username==username).first() is not None:
            error = f'Username {username} is in use.'

        if not error:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        attempt = session.get('login_attempt', 0)
        username = request.form['username']
        password = request.form['password']
        error = None
        user = User.query.filter(User.username==username).first()
        if not user:
            error = 'Incorrect username or password.'
            attempt += 1
        elif not check_password_hash(user.password, password):
            error = 'Incorrect username or password.'
            attempt += 1
        session['login_attempt'] = attempt
        if attempt > 3:
            error = 'Excessive login attempts. Please wait several hours, you rube.'

        if not error:
            session.clear()
            session['user_id'] = user.id
            return redirect(url_for('rss_feed.index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if not user_id:
        g.user = None
    else: 
        g.user = User.query.get(user_id)
        feed_group = UserFeed.query.filter(UserFeed.user_id==user_id).all()
        g.user_feed_group = [f.feed_id for f in feed_group]


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('rss_feed.index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view


def debug_only(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not current_app.debug:
            abort(404)
        return view(**kwargs)
    return wrapped_view
