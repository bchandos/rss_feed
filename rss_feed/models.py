# pylint: disable=no-member

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    password = db.Column(db.String)

    feeds = db.relationship('UserFeed', backref='user')


class Feed(db.Model):
    __tablename__ = 'feed'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    url = db.Column(db.String)

    items = db.relationship('Item', backref='feed')

class Item(db.Model):
    __tablename__ = 'item'
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.ForeignKey('feed.id'))
    title = db.Column(db.String)
    link = db.Column(db.String)
    description = db.Column(db.String)
    content = db.Column(db.Text)
    publication_date = db.Column(db.String)
    media_content = db.Column(db.String)
    guid = db.Column(db.String, unique=True)

    user_items = db.relationship('UserItem', backref='item')

class UserFeed(db.Model):
    __tablename__ = 'user_feed'
    user_id = db.Column(db.ForeignKey('user.id'), primary_key=True)
    feed_id = db.Column(db.ForeignKey('feed.id'), primary_key=True)
    user_feed_name = db.Column(db.String)
    auto_expire = db.Column(db.Boolean, default=False)
    preview_articles = db.Column(db.Boolean, default=False)

    Feed = db.relationship('Feed')

class UserItem(db.Model):
    __tablename__ = 'user_item'
    user_id = db.Column(db.ForeignKey('user.id'), primary_key=True)
    item_id = db.Column(db.ForeignKey('item.id'), primary_key=True)
    read = db.Column(db.Boolean, default=False)
    bookmark = db.Column(db.Boolean, default=False)