# -*- mode: python; coding: utf-8 -*-
"""Daemon for updating `PriceSeries`
"""

import os
import sys

# FIXME
# beautiful HACK until I get some stuff figured out.
sys.path.insert(0, '../mutil')

import datetime
import pytz
from dateutil.parser import parse as parse_dt
import json
import urllib
import requests
import logging
import time

from sqlalchemy import Integer, String, Float
import daemon
import daemon.pidfile

from mutil import simple_alchemy

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DIR_PATH = None


class PriceSeries(object):

    query_template = dict(
        period_id='6HRS',
        time_start='',
        time_end='',
        limit=100000,
    )
    date_format_template = '%Y-%m-%dT%H:%M:%S.%f0Z'  # magic
    headers = {'X-CoinAPI-Key':
               open('API_KEY').read().strip()}
    schema = [
        ('time_period_start', 'TEXT'),
        ('time_period_end', 'TEXT'),
        ('time_open', 'TEXT'),
        ('time_close', 'TEXT'),
        ('price_open', 'REAL'),
        ('price_high', 'REAL'),
        ('price_low', 'REAL'),
        ('price_close', 'REAL'),
        ('volume_traded', 'REAL'),
        ('trades_count', 'INTEGER'),
    ]

    # these are THE values we care about, so CAPS
    TIME = 'time_period_end'
    PRICE = 'price_close'

    # this is the beginning of time if we don't have any local data
    first_date = '2018-01-09T00:00:00.0000000Z'

    _session = None

    @classmethod
    def get_db_session(cls):
        if cls._session is not None:
            return cls._session
        db_path = os.path.join(os.path.abspath(DIR_PATH), 'db.sqlite3')
        cls._session = simple_alchemy.get_session(db_path)
        return cls._session

    @classmethod
    def validate_datetime_object(cls, dt):
        assert dt.tzname() == 'UTC', 'tzname==`{}`. Expected `UTC`'.format(dt.tzname())
        assert not dt.hour % 6, 'hour==`{}` not a multiple of `6`'.format(dt.hour)
        for attr in 'minute', 'second', 'microsecond':
            value = getattr(dt, attr)
            assert value == 0, 'datetime attribute `{}`==`{}`. Expected `0`'.format(attr, value)

    @classmethod
    def get_normalized_datetime(cls, dt):
        if not isinstance(dt, datetime.datetime):
            dt = parse_dt(dt)
        return dt.strftime(cls.date_format_template)

    @classmethod
    def round_up_hour(cls, dt):
        hour_increment = 6 - dt.hour % 6
        dt += datetime.timedelta(hours=hour_increment)
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt

    def __init__(self, symbol_id):
        logger.debug('creating PriceSeries object for {}'.format(symbol_id))
        self.symbol_id = symbol_id
        schema = [
            ('time_period_start', String),
            ('time_period_end', String),
            ('time_open', String),
            ('time_close', String),
            ('price_open', Float),
            ('price_high', Float),
            ('price_low', Float),
            ('price_close', Float),
            ('volume_traded', Float),
            ('trades_count', Integer),
        ]
        self.data = simple_alchemy.get_table_class(symbol_id, schema=schema)

    def get_prices_since(self, start_dt):
        """Get prices for this PriceSeries where datetime is greater or equal to `start_dt`
        """
        # Since sqlite does not have native dates/times, we get the id for the row containing
        # date (string) `start_dt` and then do a second SQL query for rows with that ID or greater.
        try:
            start_dt = parse_dt(start_dt)
        except TypeError:
            pass
        start_dt = self.get_normalized_datetime(self.round_up(start_dt))
        kwargs = {self.TIME: start_dt}
        session = self.get_db_session()
        first = session.query(self.data).filter_by(**kwargs).first()
        results = session.query(self.data).filter(id >= start_dt).first()
        return results

    def get_url(self, query_data):
        url_1 = ('https', 'rest.coinapi.io/v1', 'ohlcv/{}/history'.format(self.symbol_id))
        query = []
        for key, value in query_data.items():
            if not value:
                continue
            if isinstance(value, datetime.datetime):
                self.validate_datetime_object(value)
                value = self.get_normalized_datetime(value)
            query.append('{}={}'.format(key, value))
        query = '&'.join(query)
        url_2 = ('', query, '')
        url = urllib.parse.urlunparse(url_1 + url_2)
        return url

    def fetch(self):
        last_date = self.get_last_date_from_store()
        if last_date is None:
            logger.debug('last date for {} not found. using default of {}'.format(self.symbol_id, self.first_date))
            last_date = parse_dt(self.first_date)
        else:
            logger.debug('date of last record for {} is {}'.format(self.symbol_id, last_date))
        self.validate_datetime_object(last_date)

        now = datetime.datetime.now(tz=pytz.UTC)
        if now - last_date < datetime.timedelta(hours=6):
            logger.debug('the time is now {}. it has not been 6 hourse since {}. not fetching anything.'
                         .format(now.isoformat(), last_date))
            return {}

        first_fetch_date = last_date + datetime.timedelta(hours=6)
        query_data = dict(self.query_template)
        query_data['time_start'] = first_fetch_date
        query_data['limit'] = 1500  # just over one year of records @6hrs
        url = self.get_url(query_data)
        logger.debug('getting url {}'.format(url))
        response = requests.get(url, headers=self.headers)
        logger.info('account has {} more API requests for this time period'.format(
            response.headers['X-RateLimit-Remaining']))
        return response.json()

    def get_last_date_from_store(self):
        session = self.get_db_session()
        obj = session.query(self.data).order_by(self.data.id.desc()).first()
        if obj is None:
            return parse_dt(self.first_date)
        dt = getattr(obj, self.TIME)
        return parse_dt(dt)

    def insert(self, data):
        logger.debug('inserting {} records into table {}'.format(len(data), self.symbol_id))
        insertions = []
        for row in data:
            insertions.append(self.data(**row))
        session = self.get_db_session()
        session.add_all(insertions)
        session.commit()

    def update(self):
        data = self.fetch()
        self.insert(data)


def main(dir_path, daemon=True):

    global DIR_PATH
    DIR_PATH = dir_path

    fh = logging.FileHandler(os.path.join(dir_path, 'logs'))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    symbols = [
        'BITSTAMP_SPOT_BTC_USD',
        'BITSTAMP_SPOT_XRP_USD',
        'BITSTAMP_SPOT_ETH_USD',
        'BITSTAMP_SPOT_LTC_USD',
        'BITSTAMP_SPOT_EUR_USD',
        'BITSTAMP_SPOT_BCH_USD'
    ]

    series = []
    for symbol_id in symbols:
        series.append(PriceSeries(symbol_id))

    while True:
        for ps in series:
            ps.update()
        logger.info('sleeping for 3600s')
        time.sleep(3600)


if __name__ == '__main__':

    from mutil.simple_daemon import daemonize

    daemonize(main)
