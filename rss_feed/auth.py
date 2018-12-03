import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import abort

from rss_feed.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone() is not None:
            error = f'Username {username} is in use.'

        if not error:
            db.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                       (username, generate_password_hash(password)))
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if not user:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if not error:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('rss_feed.index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    db = get_db()
    if not user_id:
        g.user = None
    else:
        user_feeds = db.execute(
            'SELECT * from user_feeds WHERE user_id = ?', (user_id,)).fetchall()
        if user_feeds:
            # if a user doesn't yet have added feeds, this query return None
            g.user = db.execute('SELECT user.*, GROUP_CONCAT(user_feeds.feed_id) AS feed_group '
                                'FROM user JOIN user_feeds ON user.id = user_feeds.user_id '
                                'WHERE user.id = ? '
                                'GROUP BY user.id', (user_id,)).fetchone()
        else:
            # fallback for if user has no added feeds, just return user fields
            g.user = db.execute(
                'SELECT * from user WHERE id = ?', (user_id,)).fetchone()


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
