from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)


class Feed(Base):
    __tablename__ = 'feed'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)

    items = relationship('Item', backref='feed', order_by='Item.publication_date')

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    feed_id = Column(ForeignKey('feed.id'))
    title = Column(String)
    link = Column(String)
    description = Column(String)
    publication_date = Column(String)
    guid = Column(String, unique=True)

class UserFeed(Base):
    __tablename__ = 'user_feed'

    user_id = Column(ForeignKey('user.id'), primary_key=True)
    feed_id = Column(ForeignKey('feed.id'), primary_key=True)
    user_feed_name = Column(String)

class UserItem(Base):
    __tablename__ = 'user_item'
    user_id = Column(ForeignKey('user.id'), primary_key=True)
    item_id = Column(ForeignKey('item.id'), primary_key=True)
    read = Column(Boolean)
    bookmark = Column(Boolean)