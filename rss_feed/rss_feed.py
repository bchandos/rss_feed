# pylint: disable=no-member

import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from datetime import datetime
import os

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   url_for, jsonify)
from werkzeug.exceptions import abort

from rss_feed.auth import login_required, debug_only
from rss_feed.models import Feed, UserFeed, UserItem, Item, db

BASE_URL = '/rss-feed' if os.environ['FLASK_ENV'] == 'production' else ''

bp = Blueprint('rss_feed', __name__, url_prefix=f'{BASE_URL}')

def query_items(user_id, order='DESC', limit=100, offset=0, feed_id=None, bookmarks_only=False, read=False):
    q = db.session.query(Item, Feed, UserFeed, UserItem).join(Feed, Feed.id==Item.feed_id).join(UserFeed, UserFeed.feed_id==Item.feed_id).join(UserItem)
    bm_options = [True] if bookmarks_only else [True, False]
    read_options = [True, False] if read else [False]
    order_option = Item.publication_date.desc() if order=='DESC' else Item.publication_date.asc()
    if feed_id:
        return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options),
                    UserItem.read.in_(read_options),
                    Item.feed_id==feed_id).\
                    order_by(order_option).\
                    limit(limit).offset(offset).all()

    return q.filter(UserFeed.user_id==user_id, 
                    UserItem.user_id==user_id,
                    UserItem.bookmark.in_(bm_options),
                    UserItem.read.in_(read_options)).\
                    order_by(order_option).\
                    limit(limit).offset(offset).all()

@bp.before_app_first_request
def check_db():


@bp.errorhandler(404)
def error_handler(error):
    if isinstance(error, str):
        flash(error)
    return redirect(url_for('rss_feed.index'))

@bp.route('/')
@login_required
def index():
    user_id = g.user.id
    sort_param = request.args.get('sort')
    show_read = request.args.get('show_read')
    if sort_param == 'Ascending':
        order_by = 'ASC'
        sort_order_opp = 'Descending'
    else:
        order_by = 'DESC'
        sort_order_opp = 'Ascending'
    read = show_read == 'True'
    items = query_items(
        user_id=user_id, 
        order=order_by, 
        limit=25, 
        read=read
    )

    return render_template(
        'rss_feed/index.html', 
        items=items, 
        sort_order=order_by,
        sort_order_opp=sort_order_opp,
        show_read=read,
    )


@bp.route('/<int:feed_id>')
@login_required
def feed_index(feed_id):
    user_id = g.user.id
    sort_param = request.args.get('sort', None)
    show_read = request.args.get('show_read')
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
    read = show_read == 'True'
    items = query_items(
        user_id=user_id, 
        order=order_by, 
        feed_id=feed_id, 
        limit=25,
        read=read,
    )

    return render_template(
        'rss_feed/index.html',
        items=items, 
        feed_name=feed_name,
        feed_id=feed_id, 
        sort_order=order_by,
        sort_order_opp=sort_order_opp,
        show_read=read,
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
        items = query_items(
            user_id=user_id, 
            order=order_by,
            feed_id=feed_id, 
            bookmarks_only=True, 
            read=True
        )
        return render_template(
            'rss_feed/index.html', 
            items=items, 
            feed_name=feed_name, 
            feed_id=feed_id, 
            sort_order_opp=sort_order_opp,
            bookmarks=True,
        )

    items = query_items(
        user_id=user_id,
        order=order_by, 
        bookmarks_only=True, 
        read=True
    )
    return render_template(
        'rss_feed/index.html', 
        items=items, 
        sort_order_opp=sort_order_opp,
        bookmarks=True,
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
                feed_info = parse_feed_information(u.geturl())
                feed_name = feed_info['title']

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
                feed_name = existing_feed.name
            if feed_name == '':
                return redirect(url_for('rss_feed.edit_feed', id=feed_id))
            else:
                return redirect(url_for('rss_feed.index'))
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
        auto_expire = request.form.get('auto-expire', 'off') == 'on'
        preview_articles = request.form.get('content-preview', 'off') == 'on'
        feed.Feed.url = feed_url
        db.session.add(feed.Feed)
        uf = UserFeed.query.filter(UserFeed.user_id==g.user.id, UserFeed.feed_id==id).first()
        uf.user_feed_name = custom_name
        uf.auto_expire = auto_expire
        uf.preview_articles = preview_articles
        db.session.add(uf)
        db.session.commit()
        flash(f'Feed id {id} updated.')
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
    return redirect(request.referrer)

### PORT TO update_feeds.py ###

# def delete_items(user_id, feed_id):
#     # Get rid of old, read, unbookmarked items
#     old_items = db.session.query(UserItem, Item).join(Item).filter(
#         UserItem.user_id==user_id,
#         UserItem.read==True,
#         UserItem.bookmark==False,
#         Item.feed_id==feed_id
#     )
#     for item_ in old_items:
#         user_item = item_.UserItem
#         item = item_.Item
#         fourteen_days_ago = datetime.now() - timedelta(days=14)
#         if float(item.publication_date) < fourteen_days_ago.timestamp():
#             db.session.delete(user_item)
#             if len(item.user_items) <= 1:
#                 db.session.delete(item)
#     db.session.commit()

# def expire_items(user_id, feed_id):
#     # Auto mark-read for items older than 2 days
#     old_items = db.session.query(UserItem, Item).join(Item).filter(
#         UserItem.user_id==user_id,
#         UserItem.read==False,
#         Item.feed_id==feed_id
#     )
#     for item_ in old_items:
#         user_item = item_.UserItem
#         item = item_.Item
#         two_days_ago = datetime.now() - timedelta(days=2)
#         if float(item.publication_date) < datetime.timestamp(two_days_ago):
#             user_item.read = True
#     db.session.commit()


@bp.app_template_filter()
def datetimeformat(value, format='%m-%d-%Y @ %H:%M'):
    d = datetime.fromtimestamp(float(value))
    return d.strftime(format)


@bp.route('/_mark_read', methods=('POST',))
@login_required
def mark_read():
    user_id = g.user.id
    id = getattr(request.json, 'id', None) 
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
    return ''


@bp.route('/_bookmark', methods=('POST',))
@login_required
def bookmark():
    user_id = g.user.id
    id = int(getattr(request.json, 'id', 0))
    marked = getattr(request.json, 'marked', 'false')
    
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
    return ''


@bp.route('/_article_contents')
@login_required
def article_contents():
    id = request.args.get('id', 0, type=int)
    if id:
        item = Item.query.get(id)
        return jsonify(article_contents=item.content, link=item.link)
    return ''


@bp.route('/mark_read_all', methods=('POST',))
@login_required
def mark_read_all():
    user_id = g.user.id
    j = request.get_json()
    item_ids = j.get('unreadIds')
    all_items = UserItem.query.filter(
        UserItem.user_id==user_id,
        UserItem.item_id.in_(item_ids)
    ).all()
    
    for i in all_items:
        i.read = True
    db.session.commit()
    
    return jsonify(status='done')

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
    feed_id = request.args.get('feed_id')
    last_item_id = request.args.get('last_item_id')
    sort_order = request.args.get('sort_order', '')
    start_at = int(request.args.get('start_at', 0))
    show_read = request.args.get('show_read')

    read = show_read == 'True'
    # item = Item.query.get(last_item_id)

    items = query_items(
        g.user.id, 
        order=sort_order, 
        limit=25, 
        offset=start_at, 
        feed_id=int(feed_id) if feed_id else None, 
        bookmarks_only=False,
        read=read
    )
    offset = 0
    for idx, item in enumerate(items):
        if item.Item.id == last_item_id:
            offset = idx
            break
    
    if offset:
        items = query_items(
            g.user.id, 
            order=sort_order, 
            limit=25, 
            offset=start_at + offset, 
            feed_id=int(feed_id) if feed_id else None, 
            bookmarks_only=False,
            read=read
        )

    return jsonify(dict(
        new_contents=render_template(
            'rss_feed/more_articles.html', 
            items=items,
            show_read=read,
            sort_order=sort_order
        )
    ))


def download_feed(feed_url):
    try:
        req = Request(
                feed_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
        f = urlopen(req)
    except:
        return None
    
    with f:
        if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
            return ET.fromstring(f.read())
    
    return None


def parse_feed_information(feed_url):
    """ Given the feed_url, access the feed and parse the feed
        information such as title, etc.

        Handles both RSS 2.0 and Atom feed formats.
    """
    xml_file = download_feed(feed_url)
    if xml_file and xml_file.tag == 'rss':
        title = xml_file[0].find('title')
        return dict(title=title.text if title else '')
    elif xml_file and xml_file.tag == '{http://www.w3.org/2005/Atom}feed':
        ns = dict(atom='http://www.w3.org/2005/Atom')
        title = xml_file.find('atom:title', ns)
        return dict(title=title.text if title else '')
    else:
        return {}


