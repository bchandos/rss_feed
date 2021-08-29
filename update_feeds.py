from datetime import datetime
import re
from urllib.request import urlopen, Request
from psycopg2.extras import RealDictConnection
import os
import time
import xml.etree.ElementTree as ET

from dateutil.parser import parse

db = RealDictConnection(os.environ['DATABASE_URL'])

if os.environ['FLASK_ENV'] == 'development':
    WAIT_MINUTES = 2
    WAIT_SECONDS = 6
else:
    WAIT_MINUTES = 5
    WAIT_SECONDS = 60

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

def parse_feed_items(feed_url):
    """ Given the feed_url, access the feed and parse the feed
        items.

        Handles both RSS 2.0 and Atom feed formats.
    """
    xml_file = download_feed(feed_url)
    # print('>>>>', xml_file)
    item_list = list()
    if xml_file and xml_file.tag == 'rss':
        ns = dict(
            content='http://purl.org/rss/1.0/modules/content/',
            media='http://search.yahoo.com/mrss/',
        )
        all_items = xml_file[0].findall('item', ns)
        for item in all_items:
            
            title = item.find('title').text
            
            link = item.find('link').text
            
            guid = item.find('guid').text

            if (d := item.find('description')) is not None:
                description = d.text
            else:
                description = 'No description available.'
            
            if (pd := item.find('pubDate')) is not None:
                publication_date = datetime.timestamp(
                    parse(pd.text))
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
            elif '<img' in description:
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
    elif xml_file and xml_file.tag == '{http://www.w3.org/2005/Atom}feed':
        ns = dict(atom='http://www.w3.org/2005/Atom')
        all_items = xml_file.findall('atom:entry', ns)
        for item in all_items:
            
            title = item.find('atom:title', ns).text
            
            link = item.find('atom:link', ns).attrib.get('href')
            
            guid = item.find('atom:id', ns).text
            
            if (d := item.find('atom:summary', ns)) is not None:
                description = d.text
            else:
                description = 'No description available.'
            
            if (pd := item.find('atom:updated', ns)) is not None:
                publication_date = datetime.timestamp(
                    parse(pd.text))
            else:
                publication_date = datetime.timestamp(datetime.today())
            
            if (c := item.find('atom:content', ns)) is not None:
                content = c.text
            else:
                content = None
            
            if '<img' in description:
                p = re.compile(r'<img[\s\S+]?src=\"(\S+)?\"')
                if m := p.search(description):
                    media_content = m.group(1)
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
    
    return item_list

def download_items(url, feed_id):
    all_items = parse_feed_items(url)
    for item in all_items:
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

while(True):
    print(f'Feed updating started and waiting {WAIT_MINUTES} minutes...')
    for m in range(WAIT_MINUTES):
        time.sleep(WAIT_SECONDS)
        print(f'Feed updating has waited {m+1} minutes...')
    print('Feed updating has waited, now starting...')
    cur = db.cursor()
    cur.execute(""" SELECT * From feed """)
    feed_ids = cur.fetchall()
    cur.close()

    for feed in feed_ids:
        download_items(feed['url'], feed['id'])

    print('Feed updating has finished...')