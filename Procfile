web: gunicorn 'rss_feed:create_app()' --preload --timeout 45
worker: python3 update_feeds.py