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
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import null

from rss_feed.auth import login_required, debug_only
from rss_feed.models import User, Feed, UserFeed, UserItem, Item, db

bp = Blueprint('rss_feed', __name__)


def query_items(user_id, order='DESC', limit=100, offset=0, feed_id=None, bookmarks_only=False):
    q = db.session.query(Item, Feed, UserItem).join(Feed).join(UserFeed).join(UserItem)
    bm_options = [True] if bookmarks_only else [True, False]
    if feed_id:
        return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options),
                    Item.feed_id==feed_id).\
                    order_by(Item.publication_date.desc()).\
                    limit(limit).offset(offset).all()

    return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options)).\
                    order_by(Item.publication_date.desc()).\
                    limit(limit).offset(offset).all()
    

@bp.route('/')
@login_required
def index():
    
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    items = query_items(user_id=user_id, order=order_by)

    return render_template('rss_feed/index.html', items=items, sort_order_opp=sort_order_opp)


@bp.route('/<int:feed_id>')
@login_required
def feed_index(feed_id):
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    feed_name = Feed.query.get(feed_id).name
    items = query_items(user_id=user_id,
                        order=order_by, feed_id=feed_id)

    return render_template('rss_feed/index.html', items=items, feed_name=feed_name, feed_id=feed_id, sort_order_opp=sort_order_opp)


@bp.route('/bookmarks', defaults={'feed_id': None})
@bp.route('/<int:feed_id>/bookmarks')
@login_required
def bookmarked_index(feed_id):
    
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    if feed_id:
        feed_name = Feed.query.get(feed_id).name
        items = query_items(user_id=user_id, order=order_by,
                            feed_id=feed_id, bookmarks_only=True)
        return render_template('rss_feed/index.html', items=items, feed_name=feed_name, feed_id=feed_id, sort_order_opp=sort_order_opp)
    else:
        items = query_items(user_id=user_id,
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

            new_feed = Feed(url=feed_url, name=feed_name)
            db.session.add(new_feed)
            db.session.commit()
            new_uf = UserFeed(user_id=g.user.id, feed_id=new_feed.id)
            db.session.add(new_uf)
            db.session.commit()

            return redirect(url_for('rss_feed.get_items', feed_id=new_feed.id))
    return render_template('rss_feed/add_feed.html')


def get_feed(id):
    feed = Feed.query.join(UserFeed).filter(Feed.id==id, UserFeed.user_id==g.user.id).first()
    # feed = get_db().execute(
    #     'SELECT feeds.id, feeds.feed_name, feeds.feed_url, user_feeds.user_id, user_feeds.user_feed_name '
    #     'FROM feeds JOIN user_feeds ON feeds.id = (?) '
    #     'WHERE feeds.id = (?) AND user_feeds.user_id = (?)', (id, id, g.user.id)).fetchone()
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
        feed.url = feed_url
        db.session.add(feed)
        if custom_name:
            uf = UserFeed.query.filter(user_id==g.user.id, feed_id==id)
            uf.user_feed_name = custom_name
            db.session.add(uf)
        db.session.commit()
        return redirect(url_for('rss_feed.index'))
    return render_template('rss_feed/edit.html', feed=feed)


@bp.route('/user', methods=('GET',))
@login_required
def user_menu():
    user_id = g.user.id
    users_feeds = Feed.query.join(UserFeed).filter(Feed.id.in_(g.user_feed_group)).all()
    return render_template('rss_feed/user.html', users_feeds=users_feeds)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete_feed(id):
    feed_name = Feed.query.get(id).name
    user_feed = UserFeed.query.filter(UserFeed.feed_id==id).first()
    db.session.delete(user_feed)
    db.session.commit()
    flash(f'Feed {feed_name} deleted.')
    return redirect(url_for('rss_feed.index'))


@bp.route('/update', defaults={'feed_id': None})
@bp.route('/update/<int:feed_id>')
@login_required
def get_items(feed_id):
    user_id = g.user.id
    if g.user_feed_group:
        if feed_id and feed_id in g.user_feed_group:
            feed = get_feed(feed_id)
            download_items(feed.url, feed_id, user_id)
        elif not feed_id:
            for user_feed_id in g.user_feed_group:
                feed = get_feed(int(user_feed_id))
                download_items(feed.url, user_feed_id, user_id)
        else:
            abort(404, "No such feed")
    else:
        return redirect(url_for('add_feed'))
    if feed_id:
        return redirect(url_for('rss_feed.feed_index', feed_id=feed_id))
    return redirect(url_for('rss_feed.index'))


def download_items(url, feed_id, user_id):
    with urlopen(url) as f:
        if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
            xml_file = ET.fromstring(f.read())
            for item in xml_file[0].findall('item'):
                title = item.find('title').text
                link = item.find('link').text
                if item.find('description') is not None:
                    description = re.sub('<[^<]+?>', '', item.find('description').text)
                else:
                    description = 'No description available.'
                if item.find('pubDate') is not None:
                    publication_date = datetime.timestamp(
                        parse(item.find('pubDate').text))
                else:
                    publication_date = datetime.timestamp(datetime.today())
                guid = item.find('guid').text
                item_exists = Item.query.filter(Item.guid==guid).first()
                if not item_exists:
                    # Only create item if it doesn't exist
                    new_item = Item(feed_id=feed_id, title=title, link=link, description=description, publication_date=publication_date, guid=guid)
                    db.session.add(new_item)
                    db.session.commit()
                    new_ui = UserItem(user_id=user_id, item_id=new_item.id)
                    db.session.add(new_ui)
                else:
                    # Only create user_item if it doesn't exist
                    if not UserItem.query.filter(UserItem.user_id==user_id, UserItem.item_id==item_exists.id).first():
                        new_ui = UserItem(user_id=user_id, item_id=item_exists.id)
                        db.session.add(new_ui)
                db.session.commit()


@bp.app_template_filter()
def datetimeformat(value, format='%m-%d-%Y @ %H:%M'):
    d = datetime.fromtimestamp(float(value))
    return d.strftime(format)


@bp.route('/_mark_read')
# TODO make this toggle
def mark_read():
    user_id = g.user.id
    id = request.args.get('id', 0, type=int)
    if id:
        user_item = UserItem.query.filter(UserItem.user_id==user_id, UserItem.item_id==id).first()
        if user_item.read == 0:
            user_item.read = True
            # db.execute(
            #     'UPDATE user_items SET read = 1 WHERE item_id = ? AND user_id = ?', (id, user_id))
            new_status = 'Read'
        else:
            user_item.read = False
            # db.execute(
            #     'UPDATE user_items SET read = 0 WHERE item_id = ? AND user_id = ?', (id, user_id))
            new_status = 'Unread'
        db.session.add(user_item)
        db.session.commit()
        return jsonify(id=id, read=new_status)


@bp.route('/_bookmark')
def bookmark():
    user_id = g.user.id
    id = request.args.get('id', 0, type=int)
    marked = request.args.get('marked', 'false', type=str)
    
    if id:
        user_item = UserItem.query.filter(UserItem.user_id==user_id, UserItem.item_id==id).first()
        if marked == 'true':
            user_item.bookmark = False
            # db.execute(
            #     'UPDATE user_items SET bookmark = 0 WHERE item_id = ? AND user_id = ?', (id, user_id))
            bm = 'false'
            u = url_for('static', filename='icons/bookmark-icon.svg')
        else:
            user_item.bookmark = True
            # db.execute(
            #     'UPDATE user_items SET bookmark = 1 WHERE item_id = ? AND user_id = ?', (id, user_id))
            bm = 'true'
            u = url_for('static', filename='icons/bookmark-red-icon.svg')
        db.session.add(user_item)
        db.session.commit()
        return jsonify(id=id, bookmark=bm, u=u)


@bp.route('/mark_read_all', defaults={'feed_id': None})
@bp.route('/mark_read_all/<int:feed_id>')
@login_required
def mark_read_all(feed_id):
    user_id = g.user.id
    
    if not feed_id:
        Item.query.filter(user_id==user_id).update({'read': True})
        # db.execute(
        #     'UPDATE user_items SET read = 1 WHERE user_id = ?', (user_id,))
        db.session.commit()
        return redirect(url_for('rss_feed.index'))
    else:
        UserItem.query.filter(Item.feed_id==feed.id, UserItem.user_id==user_id).update({'read': True})
        # all_items = db.execute(
        #     'SELECT id FROM items WHERE feed_id = ?', (feed_id,)).fetchall()
        # for item in all_items:
        #     db.execute(
        #         'UPDATE user_items SET read = 1 WHERE item_id = ? AND user_id = ?', (item['id'], user_id))
        db.session.commit()
        return redirect(url_for('rss_feed.feed_index', feed_id=feed_id))


@bp.route('/__allunread')
@login_required
@debug_only
def all_unread():
    # debugging end point to reset all user read statuses
    user_id = g.user.id
    UserItem.query.filter(user_id==user_id).update({'read': 0})

    return redirect(url_for('rss_feed.index'))


@bp.route('/__testflash')
@login_required
@debug_only
def test_flash():
    # debugging endpoint to test flash messaging
    flash('This is a test of the flash system.')
    return redirect(url_for('rss_feed.index'))