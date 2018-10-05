import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import urlopen

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for)
from werkzeug.exceptions import abort

from rss_feed.auth import login_required
from rss_feed.db import get_db

bp = Blueprint('rss_feed', __name__)


@bp.route('/')
def index():
    db = get_db()
    user_id = g.user['id']
    items = db.execute('SELECT feeds.feed_name, items.title, items.link, items.description, items.publication_date, items.guid, user_feeds.user_id '
                       'FROM items '
                       'INNER JOIN feeds ON items.feed_id = feeds.id '
                       'INNER JOIN user_feeds on items.feed_id = user_feeds.feed_id '
                       'WHERE user_feeds.user_id = (?)', (user_id,)).fetchall()
    return render_template('rss_feed/index.html', items=items)


@bp.route('/add_feed', methods=('GET', 'POST'))
@login_required
def add_feed():
    if request.method == 'POST':
        feed_url = request.form['feed_url']
        error = None

        if not feed_url:
            error = 'Title is required.'

        if error:
            flash(error)
        else:
            # validate feed and gather feed name
            u = urlparse(feed_url, scheme='http')
            with urlopen(u.geturl()) as f:
                if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):

            db = get_db()
            db.execute(
                'INSERT INTO feeds (feed_name, feed_url) VALUES (?, ?)', (feed_url, feed_name))
            feed_id = db.cursor().lastrowid
            db.execute(
                'INSERT INTO user_feeds (user_id, feed_id) VALUES (?, ?)', (g.user['id'], feed_id))
            db.commit()
            return redirect(url_for('rss_feed.index'))
    return render_template('rss_feed/add_feed.html')


def get_feed(id):
    feed = get_db().execute(
        'SELECT feeds.feed_name, feeds.feed_url, user_feeds.user_id, user_feeds.user_feed_name '
        'FROM feeds JOIN user_feeds ON feeds.id = (?) '
        'WHERE feeds.id = (?) AND user_feeds.user_id = (?)', (id, id, g.user['id'])).fetchone()
    if not feed:
        abort(404, f'Feed id {id} doesn\'t exist.')
    return feed


@bp.route('/<int:id>/edit', methods=('GET', 'POST'))
@login_required
def edit_feed(id):
    feed = get_feed(id)
    if request.method == 'POST':
        feed_url = request.form['feed_url']
        if request.form['feed_name'] != feed['feed_name']:
            custom_name = request.form['custom_name']
        db = get_db()
        db.execute('UPDATE feeds SET feed_url = ? WHERE id = ?', (feed_url, id))
        if custom_name:
            db.execute('UPDATE user_feeds SET user_feed_name = ? WHERE user_id = ? AND feed_id = ?', (
                custom_name, g.user['id'], id))
        db.commit()
        return redirect(url_for('rss_feed.index'))
    return render_template('rss_feed/edit.html', feed=feed)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete_feed(id):
    db = get_db()
    db.execute('DELETE FROM feeds WHERE id = (?)', (id,))
    db.execute(
        'DELETE FROM user_feeds WHERE feed_id = (?) AND user_id = (?)', (id, g.user['id']))
    db.commit()
    return redirect(url_for('rss_feed.index'))
