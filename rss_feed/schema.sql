DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS feeds;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS user_feeds;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE feeds(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_name TEXT NOT NULL,
    feed_url TEXT NOT NULL
);

CREATE TABLE items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    description TEXT,
    publication_date TEXT,
    guid TEXT, 
    FOREIGN KEY (feed_id) REFERENCES feeds (id)
);

CREATE TABLE user_feeds(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    feed_id INTEGER NOT NULL,
    user_feed_name TEXT,
    FOREIGN KEY (user_id) REFERENCES user (id)
    FOREIGN KEY (feed_id) REFERENCES feeds (id)
);