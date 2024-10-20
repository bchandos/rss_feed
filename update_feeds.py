from datetime import datetime, timedelta
import re
from urllib.request import urlopen, Request
from psycopg2.extras import RealDictConnection
import os
import time
import xml.etree.ElementTree as ET

from dateutil.parser import parse

db = RealDictConnection(os.environ['DATABASE_URL'])

if os.environ.get('FLASK_DEBUG') == 'true':
    WAIT_MINUTES = int(os.environ.get('WAIT_MINUTES', 2))
    WAIT_SECONDS = 6
else:
    WAIT_MINUTES = int(os.environ.get('WAIT_MINUTES', 15))
    WAIT_SECONDS = 60

def download_feed(feed_url):
    print(f'Downloading feed {feed_url}...')
    try:
        req = Request(
                feed_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
        f = urlopen(req)
    except:
        print('Request failed!')
        return None
    
    with f:
        if f.getcode() == 200 and 'xml' in f.getheader('Content-Type'):
            return ET.fromstring(f.read())
    print(f'Request completed but bad response code ({f.getcode()}) or Content-Type header ({f.getheader("Content-Type")})')
    return None

def parse_feed_items(feed_url):
    """ Given the feed_url, access the feed and parse the feed
        items.

        Handles both RSS 2.0 and Atom feed formats.
    """
    xml_file = download_feed(feed_url)
    # print('>>>>', xml_file)
    item_list = list()
    if xml_file is not None and getattr(xml_file, 'tag', None) == 'rss':
        print('Parsing standard RSS feed...')   
        ns = dict(
            content='http://purl.org/rss/1.0/modules/content/',
            media='http://search.yahoo.com/mrss/',
        )
        all_items = xml_file[0].findall('item', ns)
        print(f'Found {len(all_items)} items...')
        for item in all_items:
            title = item.find('title')
            link = item.find('link')
            guid = item.find('guid')
            if title is None or link is None or guid is None:
                # Without all of these, it's not a valid item
                print('Missing title, link, or guid:', title, link, guid)
                continue
            title = title.text
            link = link.text
            guid = guid.text

            if (d := item.find('description')) is not None:
                description = d.text
            else:
                description = 'No description available.'
            pd = item.find('pubDate')
            if pd and pd.text: 
                publication_date = datetime.timestamp(parse(pd.text))
            else:
                publication_date = datetime.timestamp(datetime.today())
            
            if (c := item.find('content:encoded', ns)) is not None:
                content = c.text
            else:
                content = None
            if (mc := item.find('media:content', ns)) is not None:
                media_content = mc.get('url')
            elif (i := item.find('image')) is not None:
                media_content = i.text
            elif description and '<img' in description:
                p = re.compile(r'<img[\s\S+]?src=\"(\S+)?\"')
                if m := p.search(description):
                    media_content = m.group(1)
                else:
                    media_content = None
            else:
                media_content = None
            
            item_list.append(dict(
                title=title,
                link=link,
                description=description,
                publication_date=publication_date,
                content=content,
                media_content=media_content,
                guid=guid
            ))
    elif xml_file is not None and getattr(xml_file, 'tag', None) == '{http://www.w3.org/2005/Atom}feed':
        print('Parsing Atom feed...')
        ns = dict(atom='http://www.w3.org/2005/Atom')
        all_items = xml_file.findall('atom:entry', ns)
        print(f'Found {len(all_items)} items...')
        for item in all_items:
            title = item.find('atom:title', ns)
            link = item.find('atom:link', ns)
            guid = item.find('atom:id', ns)
            if title is None or link is None or guid is None:
                # Without all of these, not a valid item
                print('Missing title, link, or guid:', title, link, guid)
                continue

            title = title.text
            link = link.attrib.get('href')
            guid = guid.text
            
            if (d := item.find('atom:summary', ns)) is not None:
                description = d.text
            else:
                description = 'No description available.'
            
            pd = item.find('atom:updated', ns)
            if pd and pd.text: 
                publication_date = datetime.timestamp(parse(pd.text))
            else:
                publication_date = datetime.timestamp(datetime.today())
            
            if (c := item.find('atom:content', ns)) is not None:
                content = c.text
            else:
                content = None
            
            media_content = None
            if description and '<img' in description:
                p = re.compile(r'<img[\s\S+]?src=\"(\S+)?\"')
                if m := p.search(description):
                    media_content = m.group(1)
            
            item_list.append(dict(
                title=title,
                link=link,
                description=description,
                publication_date=publication_date,
                content=content,
                media_content=media_content,
                guid=guid
            ))
    
    return item_list

def download_items(url, feed_id):
    all_items = parse_feed_items(url)
    print(f'{len(all_items)} items downloaded from {url}.')
    for item in all_items:
        # Don't process items older than 14 days, because we delete those
        if item['publication_date'] >= datetime.timestamp(datetime.now() - timedelta(days=14)): 
            cur = db.cursor()
            # Select all users
            cur.execute(
                """ SELECT user_id FROM user_feed WHERE user_feed.feed_id=%s """, 
                (feed_id,)
            )
            users = [x['user_id'] for x in cur.fetchall()]
            # Check if items exists
            cur.execute(""" SELECT id FROM item WHERE item.guid=%s """, (item['guid'],))
            item_exists = cur.fetchone()
            if not item_exists:
                # Only create item if it doesn't exist
                cur.execute(""" 
                    INSERT INTO item
                    (feed_id, title, link, description, publication_date, guid, content, media_content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    feed_id, 
                    item['title'], 
                    item['link'], 
                    item['description'], 
                    item['publication_date'], 
                    item['guid'], 
                    item['content'],
                    item['media_content']
                ))
                
                new_item_id = cur.fetchone()['id']

                for user_id in users:
                    cur.execute(""" 
                        INSERT INTO user_item 
                        (user_id, item_id, read, bookmark) 
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, new_item_id, False, False)
                    )
                db.commit()
            else:
                # Only create user_item if it doesn't exist
                for user_id in users:
                    cur.execute(""" 
                        SELECT * FROM user_item 
                        WHERE user_item.user_id=%s
                        AND user_item.item_id=%s
                    """, (
                        user_id,
                        item_exists['id']
                    ))
                    ui_exists = cur.fetchone()
                    if not ui_exists:
                        cur.execute(""" 
                            INSERT INTO user_item
                            (user_id, item_id, read, bookmark)
                            VALUES (%s, %s, %s, %s)
                        """, (user_id, item_exists['id'], False, False)
                        )
                        db.commit()
            db.commit()

def delete_items(feed_id):
    # Get rid of old, read, unbookmarked items
    cur = db.cursor()
    cur.execute(
        """ SELECT user_id FROM user_feed WHERE user_feed.feed_id=%s """, 
        (feed_id,)
    )
    users = [x['user_id'] for x in cur.fetchall()]
    fourteen_days_ago = datetime.now() - timedelta(days=14)
    delete_date = fourteen_days_ago.timestamp()
    for user_id in users:
        cur.execute("""
            DELETE FROM user_item WHERE (user_id, item_id) IN (
                SELECT user_id, item_id FROM user_item JOIN item ON (user_item.item_id=item.id)
                WHERE 
                user_item.user_id=%s AND
                user_item.read=%s AND
                user_item.bookmark=%s AND
                item.feed_id=%s AND
                CAST(item.publication_date AS NUMERIC) < %s
            )
        """, (
            user_id, True, False, feed_id, delete_date
        ))
    
    cur.execute("""
        DELETE FROM item WHERE id IN (
            SELECT id 
            FROM item LEFT JOIN user_item ON (user_item.item_id=item.id)
            WHERE user_item IS NULL
        )
    """)

def expire_items(feed_id):
    pass


while(True):
    print('Initial wait...')
    time.sleep(WAIT_SECONDS)
    print('Feed updating has started...')
    cur = db.cursor()
    cur.execute(""" SELECT * From feed """)
    feed_ids = cur.fetchall()
    cur.close()

    for feed in feed_ids:
        download_items(feed['url'], feed['id'])
        delete_items(feed['id'])
        expire_items(feed['id'])
    print('Feed updating has finished!')

    print(f'Feed updating will wait {WAIT_MINUTES} minutes...')
    for m in range(WAIT_MINUTES):
        time.sleep(WAIT_SECONDS)
        print(f'Feed updating has waited {m+1} minutes...')
