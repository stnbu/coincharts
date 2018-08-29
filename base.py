# -*- mode: python; coding: utf-8 -*-
"""Daemon for updating `PriceSeries`
"""

import os
import sys
import datetime
import pytz
from dateutil.parser import parse as parse_dt
import sqlite3
import json
import atexit
import urllib
import requests
import logging
import time

import daemon
import daemon.pidfile

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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

    column_names = [n for n, _ in schema]
    row_template = 'INSERT INTO {{symbol_id}}({column_names}) values ({q_marks});'.\
        format(
            column_names=', '.join(column_names),
            q_marks=', '.join(['?']*len(schema))
        )

    # todo. this needs to be calculated based on the path given by user
    _sqlite_db = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')

    _connection = None

    @classmethod
    def connect(cls):
        """The sqlite connection is a class singleton.

        https://www.sqlite.org/faq.html#q5

        Since the updates are done sequentially, we're ok.
        """
        if cls._connection is None:
            logger.debug('connecting to database {}'.format(cls._sqlite_db))
            cls._connection = sqlite3.connect(cls._sqlite_db)

            def _cleanup():
                logger.debug('performing at-exit cleanup (closing database)')
                cls._connection.commit()
                cls._connection.close()
            atexit.register(_cleanup)
        return cls._connection

    @classmethod
    def validate_datetime_object(cls, dt):
        assert dt.tzname() == 'UTC', 'tzname==`{}`. Expected `UTC`'.format(dt.tzname())
        assert dt.hour in (0, 6, 12, 18)
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
    def round_up(cls, dt):
        hour_increment = 6 - dt.hour % 6
        dt += datetime.timedelta(hours=hour_increment)
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt

    def __init__(self, symbol_id, create_store=True):
        logger.debug('creating PriceSeries object for {}'.format(symbol_id))
        self.symbol_id = symbol_id
        self.row_template = self.row_template.format(symbol_id=self.symbol_id)
        if create_store:
            self._create_store()

    def get_prices_since(self, start_dt):
        """Get prices for this PriceSeries where datetime is greater or equal to `start_dt`
        """
        # Since sqlite does not have native date times, we get the rowid for the row containing
        # date `start_dt` and then do a second SQL query for rows with that ID or greater.
        try:
            start_dt = parse_dt(start_dt)
        except TypeError:
            pass
        start_dt = self.get_normalized_datetime(self.round_up(start_dt))
        sql = 'SELECT _ROWID_ FROM {symbol_id} WHERE {TIME} = \'{start_dt}\' LIMIT 1;'.format(
            symbol_id=self.symbol_id,
            TIME=self.TIME,
            start_dt=start_dt,
        )
        cursor = self.connect().cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        if len(results) != 1:
            raise Exception('Failed to get exactl one row when executing "{}"'.format(sql))
        columns, = results
        rowid, = columns
        sql = 'SELECT {TIME}, {PRICE} FROM {symbol_id} WHERE _ROWID_ >= {rowid};'.format(
            TIME=self.TIME,
            PRICE=self.PRICE,
            symbol_id=self.symbol_id,
            rowid=rowid,
        )
        cursor = self.connect().cursor()
        cursor.execute(sql)
        results = cursor.fetchall()

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

    def _create_store(self):
        logger.debug('creating table {} (if it does not exist)'.format(self.symbol_id))
        create_table = ['CREATE TABLE IF NOT EXISTS {symbol_id} (']
        #fields = ['id integer PRIMARY KEY']
        fields = []
        for name, type_ in self.schema:
            fields.append('{} {}'.format(name, type_))
        fields = ',\n'.join(fields)
        create_table.append(fields)
        create_table.append(');')
        create_table = '\n'.join(create_table)
        cursor = self.connect().cursor()
        cursor.execute(create_table.format(
            symbol_id=self.symbol_id
        ))
        self.connect().commit()

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
        logger.info('Account has {} more API requests for this time period'.format(
            response.headers['X-RateLimit-Remaining']))
        return response.json()

    def get_last_date_from_store(self):
        sql = 'SELECT {the_columns} FROM {symbol_id} ORDER BY _ROWID_ DESC LIMIT 1;'.format(
            the_columns=', '.join((self.TIME, self.PRICE)),
            symbol_id=self.symbol_id,
        )
        cursor = self.connect().cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        last_row, = results
        last_date = parse_dt(last_row[0])
        return last_date

    def insert(self, data):
        logger.debug('inserting {} records into table {}'.format(len(data), self.symbol_id))
        insert_rows = []
        for row in data:
            values = [None] * len(self.schema)
            for key, value in row.items():
                index = self.column_names.index(key)
                values[index] = value
            assert all(map(lambda x: x is not None, values)), 'Tried to insert None: {}'.format(values)
            insert_rows.append(values)
        if insert_rows:
            try:
                cursor = self.connect().cursor()
                cursor.executemany(self.row_template, insert_rows)
            finally:
                logger.debug('done inserting. committing...')
                self.connect().commit()

    def update(self):
        data = self.fetch()
        self.insert(data)


def main(dir_path):

    # when I'm a daemon, log all exceptions
    def exception_handler(type_, value, tb):
        logger.exception('uncaught exception: {}'.format(str(value)))
        sys.__excepthook__(type_, value, tb)
    sys.excepthook = exception_handler

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

    if len(sys.argv) == 1:
        print('usage: {} [--daemon] <directory>'.format(os.path.basename(__file__)))
        sys.exit(1)

    # no need to involve argparse for something this simple
    DAEMON = True
    if '--daemon' in sys.argv:
        script_name, _, dir_path = sys.argv
    else:
        script_name, dir_path = sys.argv
        DAEMON = False

    logger.debug('starting daemon {} using path {}'.format(script_name, dir_path))

    if DAEMON:
        with daemon.DaemonContext(
                working_directory=dir_path,
                pidfile=daemon.pidfile.PIDLockFile(os.path.join(dir_path, 'pid')),

        ):
            main(dir_path)
    else:
        main(dir_path)
