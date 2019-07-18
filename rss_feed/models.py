from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    password = db.Column(db.String)


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
    publication_date = db.Column(db.String)
    guid = db.Column(db.String, unique=True)

class UserFeed(db.Model):
    __tablename__ = 'user_feed'
    user_id = db.Column(db.ForeignKey('user.id'), primary_key=True)
    feed_id = db.Column(db.ForeignKey('feed.id'), primary_key=True)
    user_feed_name = db.Column(db.String)

class UserItem(db.Model):
    __tablename__ = 'user_item'
    user_id = db.Column(db.ForeignKey('user.id'), primary_key=True)
    item_id = db.Column(db.ForeignKey('item.id'), primary_key=True)
    read = db.Column(db.Boolean)
    bookmark = db.Column(db.Boolean)