import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import urlopen
from datetime import datetime
import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for, jsonify)
from werkzeug.exceptions import abort
from dateutil.parser import parse

from rss_feed.auth import login_required
from rss_feed.db import get_db

bp = Blueprint('rss_feed', __name__)


@bp.route('/')
@login_required
def index():
    db = get_db()
    user_id = g.user['id']
    items = db.execute('SELECT items.id, feeds.feed_name, items.feed_id, items.title, '
                       'items.link, items.description, items.publication_date, '
                       'items.guid, user_feeds.user_id, user_items.read '
                       'FROM items '
                       'INNER JOIN feeds ON items.feed_id = feeds.id '
                       'INNER JOIN user_feeds on items.feed_id = user_feeds.feed_id '
                       'INNER JOIN user_items on items.id = user_items.item_id '
                       'WHERE user_feeds.user_id = ? AND user_items.user_id = ? '
                       'ORDER BY items.publication_date DESC', (user_id, user_id)).fetchall()
    return render_template('rss_feed/index.html', items=items)


@bp.route('/<int:feed_id>')
@login_required
def feed_index(feed_id):
    db = get_db()
    user_id = g.user['id']
    feed_name = db.execute(
        'SELECT feed_name FROM feeds WHERE id = ?', (feed_id,)).fetchone()['feed_name']
    items = db.execute('SELECT items.id, feeds.feed_name, items.feed_id, items.title, '
                       'items.link, items.description, items.publication_date, '
                       'items.guid, user_feeds.user_id, user_items.read '
                       'FROM items '
                       'INNER JOIN feeds ON items.feed_id = feeds.id '
                       'INNER JOIN user_feeds on items.feed_id = user_feeds.feed_id '
                       'INNER JOIN user_items on items.id = user_items.item_id '
                       'WHERE user_feeds.user_id = ? '
                       'AND user_items.user_id = ? '
                       'AND items.feed_id = ? '
                       'ORDER BY items.publication_date DESC', (user_id, user_id, feed_id)).fetchall()
    return render_template('rss_feed/index.html', items=items, feed_name=feed_name, feed_id=feed_id)


@bp.route('/add_feed', methods=('GET', 'POST'))
@login_required
def add_feed():
    if request.method == 'POST':
        feed_url = request.form['feed_url']
        error = None

        if not feed_url:
            error = 'URL is required.'

        if error:
            flash(error)
        else:
            # validate feed and gather feed name
            u = urlparse(feed_url, scheme='http')
            with urlopen(u.geturl()) as f:
                if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
                    root = ET.fromstring(f.read())
                    feed_name = root[0].find('title').text
                else:
                    abort(404, f'Invalid feed URL ({feed_url}).')

            db = get_db()
            feed_id = db.execute(
                'INSERT INTO feeds (feed_url, feed_name) VALUES (?, ?)', (feed_url, feed_name)).lastrowid
            # TODO figure out if lastrowid method is possible
            db.execute(
                'INSERT INTO user_feeds (user_id, feed_id) VALUES (?, ?)', (g.user['id'], feed_id))
            db.commit()
            return redirect(url_for('rss_feed.get_items', feed_id=feed_id))
    return render_template('rss_feed/add_feed.html')


def get_feed(id):
    feed = get_db().execute(
        'SELECT feeds.id, feeds.feed_name, feeds.feed_url, user_feeds.user_id, user_feeds.user_feed_name '
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
    db.execute('DELETE FROM feeds WHERE id = ?', (id,))
    db.execute(
        'DELETE FROM user_feeds WHERE feed_id = ? AND user_id = ?', (id, g.user['id']))
    db.execute('DELETE FROM items WHERE feed_id = ?', (id,))
    db.commit()
    return redirect(url_for('rss_feed.index'))


@bp.route('/update', defaults={'feed_id': None})
@bp.route('/update/<int:feed_id>')
@login_required
def get_items(feed_id):
    user_id = g.user['id']
    if 'feed_group' in g.user.keys():
        if feed_id and str(feed_id) in g.user['feed_group']:
            feed = get_feed(feed_id)
            download_items(feed['feed_url'], feed_id, user_id)
        elif not feed_id:
            for user_feed_id in g.user['feed_group'].split(','):
                feed = get_feed(int(user_feed_id))
                download_items(feed['feed_url'], user_feed_id, user_id)
        else:
            abort(404, 'No such feed.')
    else:
        return redirect(url_for('add_feed'))
    if feed_id:
        return redirect(url_for('rss_feed.feed_index', feed_id=feed_id))
    return redirect(url_for('index'))


def download_items(url, feed_id, user_id):
    db = get_db()
    with urlopen(url) as f:
        if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
            xml_file = ET.fromstring(f.read())
            for item in xml_file[0].findall('item'):
                title = item.find('title').text
                link = item.find('link').text
                description = re.sub(
                    '<[^<]+?>', '', item.find('description').text)
                publication_date = datetime.timestamp(
                    parse(item.find('pubDate').text))
                guid = item.find('guid').text
                item_id = db.execute('INSERT OR IGNORE INTO items (feed_id, title, link, description, publication_date, guid) VALUES (?, ?, ?, ?, ?, ?)',
                                     (feed_id, title, link, description, publication_date, guid)).lastrowid
                db.execute(
                    'INSERT OR IGNORE INTO user_items (user_id, item_id, read) VALUES (?, ?, 0)', (user_id, item_id))
            db.commit()


@bp.app_template_filter()
def datetimeformat(value, format='%m-%d-%Y @ %H:%M'):
    d = datetime.fromtimestamp(float(value))
    return d.strftime(format)


@bp.route('/_mark_read')
def mark_read():
    user_id = g.user['id']
    id = request.args.get('id', 0, type=int)
    db = get_db()
    if id:
        db.execute(
            'UPDATE user_items SET read = 1 WHERE item_id = ? AND user_id = ?', (id, user_id))
        db.commit()
        return jsonify(id=id, read='Read')
