FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -s /bin/bash www

CMD uwsgi /usr/src/app/uwsgi.ini 2>&1 | logger -n 10.89.0.116 -P 1514 -d & python update_feeds.py
