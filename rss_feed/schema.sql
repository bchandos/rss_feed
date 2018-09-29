DROP TABLE IF EXISTS feeds;
DROP TABLE IF EXISTS items;

CREATE TABLE feeds(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_name TEXT NOT NULL;
    feed_url TEXT NOT NULL;

);

CREATE TABLE items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    item_description TEXT,
    publication_date DATE,
    item_guid TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds (id)

);