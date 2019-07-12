import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for, jsonify)
from werkzeug.exceptions import abort
from dateutil.parser import parse

from rss_feed.auth import login_required, debug_only
from rss_feed.db import get_db

bp = Blueprint('rss_feed', __name__)


def query_items(db, user_id, order='DESC', feed_id=None, bookmarks_only=False):
    query_augment = ''
    if feed_id:
        query_augment += 'AND items.feed_id = ? '
        query_vars = (user_id, user_id, feed_id)
    else:
        query_vars = (user_id, user_id)
    if bookmarks_only:
        query_augment += 'AND user_items.bookmark = 1 '
    query_augment += f'ORDER BY items.publication_date {order}'
    return db.execute('SELECT items.id, feeds.feed_name, items.feed_id, items.title, '
                      'items.link, items.description, items.publication_date, '
                      'items.guid, user_feeds.user_id, user_items.read, user_items.bookmark '
                       'FROM items '
                       'INNER JOIN feeds ON items.feed_id = feeds.id '
                       'INNER JOIN user_feeds on items.feed_id = user_feeds.feed_id '
                       'INNER JOIN user_items on items.id = user_items.item_id '
                       'WHERE user_feeds.user_id = ? AND user_items.user_id = ? '
                       + query_augment, query_vars).fetchall()


@bp.route('/')
@login_required
def index():
    db = get_db()
    user_id = g.user['id']
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    items = query_items(db=db, user_id=user_id, order=order_by)

    return render_template('rss_feed/index.html', items=items, sort_order_opp=sort_order_opp)


@bp.route('/<int:feed_id>')
@login_required
def feed_index(feed_id):
    db = get_db()
    user_id = g.user['id']
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    feed_name = db.execute(
        'SELECT feed_name FROM feeds WHERE id = ?', (feed_id,)).fetchone()['feed_name']
    items = query_items(db=db, user_id=user_id,
                        order=order_by, feed_id=feed_id)

    return render_template('rss_feed/index.html', items=items, feed_name=feed_name, feed_id=feed_id, sort_order_opp=sort_order_opp)


@bp.route('/bookmarks', defaults={'feed_id': None})
@bp.route('/<int:feed_id>/bookmarks')
@login_required
def bookmarked_index(feed_id):
    db = get_db()
    user_id = g.user['id']
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    if feed_id:
        feed_name = db.execute(
        'SELECT feed_name FROM feeds WHERE id = ?', (feed_id,)).fetchone()['feed_name']
        items = query_items(db=db, user_id=user_id, order=order_by,
                            feed_id=feed_id, bookmarks_only=True)
        return render_template('rss_feed/index.html', items=items, feed_name=feed_name, feed_id=feed_id, sort_order_opp=sort_order_opp)
    else:
        items = query_items(db=db, user_id=user_id,
                            order=order_by, bookmarks_only=True)
        return render_template('rss_feed/index.html', items=items, sort_order_opp=sort_order_opp)


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
            try:
                with urlopen(u.geturl()) as f:
                    if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
                        root = ET.fromstring(f.read())
                        feed_name = root[0].find('title').text
                    else:
                        abort(404, f'Invalid feed URL ({feed_url}). Code {f.getcode()}.')
            except (URLError, HTTPError) as err:
                abort(404, f'URL ({feed_url}) could not be opened. Error: {err}.')

            db = get_db()
            feed_id = db.execute(
                'INSERT INTO feeds (feed_url, feed_name) VALUES (?, ?)', (feed_url, feed_name)).lastrowid
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


@bp.route('/user', methods=('GET',))
@login_required
def user_menu():
    user_id = g.user['id']
    db = get_db()
    users_feeds = db.execute('SELECT feeds.feed_name, feeds.id, user_feeds.user_id '
                             'FROM feeds '
                             'INNER JOIN user_feeds ON user_feeds.feed_id = feeds.id '
                             'WHERE user_feeds.user_id = ?', (user_id,)
                             ).fetchall()
    return render_template('rss_feed/user.html', users_feeds=users_feeds)


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
    return redirect(url_for('rss_feed.index'))


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
                if item.find('pubDate') is not None:
                    publication_date = datetime.timestamp(
                        parse(item.find('pubDate').text))
                else:
                    publication_date = datetime.timestamp(datetime.today())
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
# TODO make this toggle
def mark_read():
    user_id = g.user['id']
    id = request.args.get('id', 0, type=int)
    db = get_db()
    if id:
        read_status = db.execute('SELECT read FROM user_items WHERE item_id = ? AND user_id = ?', (id, user_id)).fetchone()
        if read_status['read'] == 0:
            db.execute(
                'UPDATE user_items SET read = 1 WHERE item_id = ? AND user_id = ?', (id, user_id))
            new_status = 'Read'
        else:
            db.execute(
                'UPDATE user_items SET read = 0 WHERE item_id = ? AND user_id = ?', (id, user_id))
            new_status = 'Unread'
        db.commit()
        return jsonify(id=id, read=new_status)


@bp.route('/_bookmark')
def bookmark():
    user_id = g.user['id']
    id = request.args.get('id', 0, type=int)
    marked = request.args.get('marked', 'false', type=str)
    db = get_db()
    if id:
        if marked == 'true':
            db.execute(
                'UPDATE user_items SET bookmark = 0 WHERE item_id = ? AND user_id = ?', (id, user_id))
            bm = 'false'
            u = url_for('static', filename='icons/bookmark-icon.svg')
        else:
            db.execute(
                'UPDATE user_items SET bookmark = 1 WHERE item_id = ? AND user_id = ?', (id, user_id))
            bm = 'true'
            u = url_for('static', filename='icons/bookmark-red-icon.svg')
        db.commit()
        return jsonify(id=id, bookmark=bm, u=u)


@bp.route('/mark_read_all', defaults={'feed_id': None})
@bp.route('/mark_read_all/<int:feed_id>')
@login_required
def mark_read_all(feed_id):
    user_id = g.user['id']
    db = get_db()
    if not feed_id:
        db.execute(
            'UPDATE user_items SET read = 1 WHERE user_id = ?', (user_id,))
        db.commit()
        return redirect(url_for('rss_feed.index'))
    else:
        all_items = db.execute(
            'SELECT id FROM items WHERE feed_id = ?', (feed_id,)).fetchall()
        for item in all_items:
            db.execute(
                'UPDATE user_items SET read = 1 WHERE item_id = ? AND user_id = ?', (item['id'], user_id))
        db.commit()
        return redirect(url_for('rss_feed.feed_index', feed_id=feed_id))


@bp.route('/__allunread')
@login_required
@debug_only
def all_unread():
    # debugging end point to reset all user read statuses
    user_id = g.user['id']
    db = get_db()
    db.execute('UPDATE user_items SET read = 0 WHERE user_id = ?', (user_id,))
    db.commit()
    return redirect(url_for('rss_feed.index'))


@bp.route('/__testflash')
@login_required
@debug_only
def test_flash():
    # debugging endpoint to test flash messaging
    flash('This is a test of the flash system.')
    return redirect(url_for('rss_feed.index'))