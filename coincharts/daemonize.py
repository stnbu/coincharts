# -*- mode: python; coding: utf-8 -*-
"""Daemon for updating `PriceSeries`
"""

import os
import sys

import datetime
import pytz
from dateutil.parser import parse as parse_dt
import urllib
import requests
import logging
import logging.handlers
import time

import daemon
import daemon.pidfile

from coincharts import config, db
from coincharts.models import THE_DATETIME_FIELD, THE_PRICE_FIELD
from coincharts.data import date_format_template

# We're replacing the module with a dict. Importing the file shouldn't result in reading from disk, etc. That's why.
config = config.get_config()

from coincharts import logger

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


class PriceSeries(object):

    query_template = dict(
        period_id='6HRS',
        time_start='',
        time_end='',
        limit=100000,
    )
    headers = {'X-CoinAPI-Key': config['api_key']}

    # this is the beginning of time if we don't have any local data
    first_date = '2018-01-09T00:00:00.0000000Z'

    @classmethod
    def validate_datetime_object(cls, dt):
        if isinstance(dt, str):
            dt = parse_dt(dt)
        assert dt.tzname() == 'UTC', 'tzname==`{}`. Expected `UTC`'.format(dt.tzname())
        assert not dt.hour % 6, 'hour==`{}` not a multiple of `6`'.format(dt.hour)
        for attr in 'minute', 'second', 'microsecond':
            value = getattr(dt, attr)
            assert value == 0, 'datetime attribute `{}`==`{}`. Expected `0`'.format(attr, value)

    @classmethod
    def get_normalized_datetime(cls, dt):
        if not isinstance(dt, datetime.datetime):
            dt = parse_dt(dt)
        return dt.strftime(date_format_template)

    @classmethod
    def round_up_hour(cls, dt):
        hour_increment = 6 - dt.hour % 6
        dt += datetime.timedelta(hours=hour_increment)
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt

    def __init__(self, symbols, dir_path):
        self.symbols = symbols
        self.dir_path = dir_path

    def get_url(self, symbol, query_data):
        url_beginning = ('https', 'rest.coinapi.io/v1', 'ohlcv/{}/history'.format(symbol))
        query = []
        for key, value in query_data.items():
            if not value:
                continue
            if isinstance(value, datetime.datetime):
                self.validate_datetime_object(value)
                value = self.get_normalized_datetime(value)
            query.append('{}={}'.format(key, value))
        query = '&'.join(query)
        url_end = ('', query, '')
        url = urllib.parse.urlunparse(url_beginning + url_end)
        return url

    def fetch(self, symbol):
        last_date = self.get_last_date_from_store(symbol)
        if last_date is None:
            logger.debug('last date for {} not found. using default of {}'.format(symbol, self.first_date))
            last_date = parse_dt(self.first_date)
        else:
            logger.debug('date of last record for {} is {}'.format(symbol, last_date))
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
        url = self.get_url(symbol, query_data)
        logger.debug('getting url {}'.format(url))
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            logger.error('request {} failed: {}'.format(url, response.reason))
            return {}
        logger.info('account has {} more API requests for this time period'.format(
            response.headers['X-RateLimit-Remaining']))
        data = response.json()
        # validate the FIRST date from the data returned. Not perfect, but will prevent future heartache.
        self.validate_datetime_object(data[0][THE_DATETIME_FIELD])
        return data

    def get_last_date_from_store(self, symbol):
        try:
            obj = db.Prices.objects.filter(symbol=symbol).order_by('id').latest()
        except db.Prices.DoesNotExist:
            logging.info('No `time_period_end` value found for {}'.format(symbol))
            return None
        dt = getattr(obj, 'dt')
        return parse_dt(dt)

    def insert(self, symbol, data):
        logger.debug('inserting {} records for symbol {}'.format(len(data), symbol))
        insertions = []
        for row in data:
            insertions.append(db.Prices(symbol=symbol, **row))
        # `.save()` done by django orm after `bulk_create`
        db.Prices.objects.bulk_create(insertions)

    def update(self):
        # TODO: probably opportunities for parallelization
        for symbol in self.symbols:
            data = self.fetch(symbol)
            self.insert(symbol, data)


def worker(dir_path, daemonize=True):

    fh = logging.FileHandler(os.path.join(dir_path, 'logs'))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # TODO: SysLogHandler will not complain if socket not present. What do?
    sh = logging.handlers.SysLogHandler(address='/var/run/syslog')
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)

    series = PriceSeries(config['history_symbols'], dir_path)

    while True:
        series.update()
        logger.info('sleeping for 3600s')
        time.sleep(3600)


def main():

    script_basename, _ = os.path.splitext(os.path.basename(__file__))

    # no need to involve argparse for something this simple
    if len(sys.argv) == 1:
        print('usage: {} [--daemon] <directory>'.format(script_basename))
        sys.exit(1)

    daemonize = True
    if '--daemon' in sys.argv:
        script_name, _, dir_path = sys.argv
    else:
        script_name, dir_path = sys.argv
        daemonize = False

    dir_path = os.path.abspath(dir_path)

    if daemonize:
        # when I'm a daemon, log all exceptions
        def exception_handler(type_, value, tb):
            logger.exception('uncaught exception on line {}; {}: {}'.format(
                tb.tb_lineno,
                type_.__name__,
                value,
            ))
            sys.__excepthook__(type_, value, tb)
        sys.excepthook = exception_handler

    logger.debug('starting daemon {} using path {}'.format(script_name, dir_path))

    if daemonize:
        pid_file = os.path.join(dir_path, script_basename + '.pid')
        with daemon.DaemonContext(
                working_directory=dir_path,
                pidfile=daemon.pidfile.PIDLockFile(pid_file),

        ):
            worker(dir_path, daemonize=daemonize)
    else:
        worker(dir_path, daemonize=daemonize)


if __name__ == '__main__':
    main()
