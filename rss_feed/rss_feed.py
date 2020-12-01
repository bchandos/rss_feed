# pylint: disable=no-member

import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime, timedelta
import time
import re

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for, jsonify, make_response)
from werkzeug.exceptions import abort
from dateutil.parser import parse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, OperationalError

from rss_feed.auth import login_required, debug_only
from rss_feed.models import User, Feed, UserFeed, UserItem, Item, db

bp = Blueprint('rss_feed', __name__)


def query_items(user_id, order='DESC', limit=100, offset=0, feed_id=None, bookmarks_only=False):
    q = db.session.query(Item, Feed, UserFeed, UserItem).join(Feed, Feed.id==Item.feed_id).join(UserFeed, UserFeed.feed_id==Item.feed_id).join(UserItem)
    bm_options = [True] if bookmarks_only else [True, False]
    order_option = Item.publication_date.desc() if order=='DESC' else Item.publication_date.asc()
    if feed_id:
        return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options),
                    Item.feed_id==feed_id).\
                    order_by(order_option).\
                    limit(limit).offset(offset).all()

    return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options)).\
                    order_by(order_option).\
                    limit(limit).offset(offset).all()

@bp.before_app_first_request
def check_db():
    try:
        db.create_all()
        db.session.commit()
    except:
        raise


@bp.errorhandler(404)
def error_handler(error):
    if isinstance(error, str):
        flash(error)
    return redirect(url_for('rss_feed.index'))

@bp.route('/')
@login_required
def index():
    last_updated = request.cookies.get('lastUpdated', '0')
    if time.time() - float(last_updated) > 1800: # 30 minutes
        return redirect(url_for('rss_feed.get_items'))
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    items = query_items(user_id=user_id, order=order_by, limit=105)

    more_read = False
    more_unread = False
    if len(items) > 100:
        xtra_items = items[100:]
        more_unread = any([i.UserItem.read for i in xtra_items])
        more_read = any([not i.UserItem.read for i in xtra_items])

    return render_template(
        'rss_feed/index.html', 
        items=items[:100], 
        sort_order_opp=sort_order_opp,
        more_read=more_read,
        more_unread=more_unread,
        )


@bp.route('/<int:feed_id>')
@login_required
def feed_index(feed_id):
    last_updated = request.cookies.get('lastUpdated', '0')
    if time.time() - float(last_updated) > 1800: # 30 minutes
        return redirect(url_for('rss_feed.get_items', feed_id=feed_id))
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    user_feed = UserFeed.query.filter(UserFeed.user_id==user_id, UserFeed.feed_id==feed_id).first()
    if user_feed.user_feed_name:
        feed_name = user_feed.user_feed_name
    else:
        feed_name = Feed.query.get(feed_id).name    
    items = query_items(user_id=user_id,
                        order=order_by, feed_id=feed_id, limit=105)

    more_read = False
    more_unread = False
    if len(items) > 100:
        xtra_items = items[100:]
        more_unread = any([i.UserItem.read for i in xtra_items])
        more_read = any([not i.UserItem.read for i in xtra_items])

    return render_template(
        'rss_feed/index.html',
        items=items[:100], 
        feed_name=feed_name,
        feed_id=feed_id, 
        sort_order_opp=sort_order_opp,
        more_read=more_read,
        more_unread=more_unread,
        )


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
        return render_template(
            'rss_feed/index.html', 
            items=items, 
            feed_name=feed_name, 
            feed_id=feed_id, 
            sort_order_opp=sort_order_opp,
            more_read=True,
            more_unread=False,
            )

    items = query_items(user_id=user_id,
                        order=order_by, bookmarks_only=True)
    return render_template(
        'rss_feed/index.html', 
        items=items, 
        sort_order_opp=sort_order_opp,
        more_read=True,
        more_unread=False,
        )


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
            existing_feed = Feed.query.filter(Feed.url==u.geturl()).first()
            if not existing_feed:
                try:
                    with urlopen(u.geturl()) as f:
                        if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
                            root = ET.fromstring(f.read())
                            feed_name = root[0].find('title').text
                        else:
                            abort(404, f'Invalid feed URL ({feed_url}). Code {f.getcode()}.')
                except (URLError, HTTPError) as err:
                    abort(404, f'URL ({feed_url}) could not be opened. Error: {err}.')

                new_feed = Feed(url=u.geturl(), name=feed_name)
                db.session.add(new_feed)
                db.session.commit()
                new_uf = UserFeed(user_id=g.user.id, feed_id=new_feed.id)
                db.session.add(new_uf)
                db.session.commit()
                feed_id = new_feed.id
            else:
                new_uf = UserFeed(user_id=g.user.id, feed_id=existing_feed.id)
                db.session.add(new_uf)
                db.session.commit()
                feed_id = existing_feed.id
            return redirect(url_for('rss_feed.get_items', feed_id=feed_id))
    return render_template('rss_feed/add_feed.html')


def get_feed(id):
    feed = db.session.query(Feed, UserFeed).filter(Feed.id==id, UserFeed.feed_id==id, UserFeed.user_id==g.user.id).first()
    if not feed:
        flash(f'Feed id {id} doesn\'t exist.')
        abort(404)
    return feed


@bp.route('/<int:id>/edit', methods=('GET', 'POST'))
@login_required
def edit_feed(id):
    feed = get_feed(id)
    if request.method == 'POST':
        custom_name = None
        feed_url = request.form['feed_url']
        if request.form['feed_name'] != feed.Feed.name:
            custom_name = request.form['feed_name']
        feed.Feed.url = feed_url
        db.session.add(feed.Feed)
        if custom_name:
            uf = UserFeed.query.filter(UserFeed.user_id==g.user.id, UserFeed.feed_id==id).first()
            uf.user_feed_name = custom_name
            db.session.add(uf)
        db.session.commit()
        return redirect(url_for('rss_feed.index'))
    return render_template('rss_feed/edit.html', feed=feed)


@bp.route('/user', methods=('GET',))
@login_required
def user_menu():
    user_id = g.user.id
    users_feeds = db.session.query(Feed, UserFeed).\
        join(UserFeed).\
        filter(Feed.id.in_(g.user_feed_group),
               UserFeed.user_id==user_id).all()
    return render_template('rss_feed/user.html', users_feeds=users_feeds)


@bp.route('/<int:id>/delete', methods=('GET',))
@login_required
def delete_feed(id):
    feed_name = Feed.query.get(id).name
    user_feed = UserFeed.query.filter(UserFeed.feed_id==id).first()
    db.session.delete(user_feed)
    db.session.commit()
    flash(f'Feed {feed_name} deleted.')
    print(request.referrer)
    return redirect(request.referrer)


@bp.route('/update', defaults={'feed_id': None})
@bp.route('/update/<int:feed_id>')
@login_required
def get_items(feed_id):
    user_id = g.user.id
    if g.user_feed_group:
        if feed_id and feed_id in g.user_feed_group:
            feed = get_feed(feed_id)
            download_items(feed.Feed.url, feed_id, user_id)
            delete_items(user_id, feed_id)
        elif not feed_id:
            for user_feed_id in g.user_feed_group:
                feed = get_feed(int(user_feed_id))
                download_items(feed.Feed.url, user_feed_id, user_id)
                delete_items(user_id, user_feed_id)
        else:
            abort(404, "No such feed")
    else:
        response = make_response(redirect(url_for('rss_feed.add_feed')))
        response.set_cookie('lastUpdated', str(time.time()), max_age=5000000)
        return response
    if feed_id:
        response = make_response(redirect(url_for('rss_feed.feed_index', feed_id=feed_id)))
        response.set_cookie('lastUpdated', str(time.time()), max_age=5000000)
        return response
    response = make_response(redirect(url_for('rss_feed.index')))
    response.set_cookie('lastUpdated', str(time.time()), max_age=5000000)
    return response


def download_items(url, feed_id, user_id):
    try:
        f = urlopen(url)
    except:
        return
    else:
        with f:
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


def delete_items(user_id, feed_id):
    # Get rid of old, read, unbookmarked items
    old_items = db.session.query(UserItem, Item).join(Item).filter(
        UserItem.user_id==user_id,
        UserItem.read==True,
        UserItem.bookmark==False,
        Item.feed_id==feed_id
    )
    for item_ in old_items:
        user_item = item_.UserItem
        item = item_.Item
        two_weeks_ago = datetime.now() - timedelta(days=14)
        if float(item.publication_date) < datetime.timestamp(two_weeks_ago):
            db.session.delete(user_item)
            # if len(item.user_items) <= 1:
            #     db.session.delete(item)
    db.session.commit()


@bp.app_template_filter()
def datetimeformat(value, format='%m-%d-%Y @ %H:%M'):
    d = datetime.fromtimestamp(float(value))
    return d.strftime(format)


@bp.route('/_mark_read')
def mark_read():
    user_id = g.user.id
    id = request.args.get('id', 0, type=int)
    if id:
        user_item = UserItem.query.filter(UserItem.user_id==user_id, UserItem.item_id==id).first()
        if user_item.read == 0:
            user_item.read = True
            new_status = 'Read'
        else:
            user_item.read = False
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
            bm = 'false'
        else:
            user_item.bookmark = True
            bm = 'true'
        db.session.add(user_item)
        db.session.commit()
        return jsonify(id=id, bookmark=bm)


@bp.route('/mark_read_all', defaults={'feed_id': None})
@bp.route('/mark_read_all/<int:feed_id>')
@login_required
def mark_read_all(feed_id):
    user_id = g.user.id
    
    if not feed_id:
        UserItem.query.filter(UserItem.user_id==user_id).update({'read': True})
        db.session.commit()
        return redirect(url_for('rss_feed.index'))
    else:

        all_items = UserItem.query.filter(Item.feed_id==feed_id, UserItem.user_id==user_id)
        for item in all_items:
            item.read = True
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


@bp.route('/_more_articles/')
@login_required
def more_articles():
    feed_id = int(request.args.get('feed_id'))
    start_at = int(request.args.get('start_at'))
    items = query_items(
        g.user.id, 
        order='DESC', 
        limit=105, 
        offset=start_at, 
        feed_id=feed_id, 
        bookmarks_only=False
    )

    more_read = False
    more_unread = False
    if len(items) > 100:
        xtra_items = items[100:]
        more_unread = any([i.UserItem.read for i in xtra_items])
        more_read = any([not i.UserItem.read for i in xtra_items])

    return render_template(
        'rss_feed/more_articles.html', 
        items=items[:100],
        more_read=more_read,
        more_unread=more_unread,
        new_length=start_at + len(items),
    )