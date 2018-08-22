# -*- mode: python; coding: utf-8 -*-
""" Having fun with https://www.coinapi.io/
"""

import requests
import dbm
import collections
import json
import urllib
import logging
import websocket

import redis

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RESTException(Exception):
    pass


API_KEY = open('API_KEY').read().strip()
DB_NAME = 'coinapi.cache'


class SillyDB(collections.abc.MutableMapping):
    """ It's called "SillyDB". Don't judge!!

    >>> db[location, query] = code_int, dictlike_data

    is transparently stored in the dbm as

    >>> db[location+'\t'+query] = str(code_int) + json.dumps(dictlike_data)

    The point is to not use up my API quota needlessly, not performance or robustness...
    """

    _key_sep = '\t'

    def __init__(self):
        self.data = dbm.open(DB_NAME, 'c')

    def _enc_key(self, location, query):
        # "normalize" location, query
        url = urllib.parse.urlparse(urllib.parse.urlunparse(('', '', location, '', query, '')))
        return url.path + self._key_sep + url.query

    def _dec_key(self, key):
        return key.split(self._key_sep)

    def _enc_value(self, status, text):
        return str(status) + json.dumps(text)

    def _dec_value(self, value):
        return int(value[:3]), json.loads(value[3:])

    def __getitem__(self, key):
        key = self._enc_key(*key)
        return self._dec_value(self.data[key])

    def __setitem__(self, key, value):
        key = self._enc_key(*key)
        self.data[key] = self._enc_value(*value)

    def __contains__(self, key):
        key = self._enc_key(*key)
        return key in self.data

    def __delitem__(self, key):
        key = self._enc_key(*key)
        del self.data[key]

    def __iter__(self):
        return map(self._dec_key, self.data.keys())

    def __len__(self):
        return len(self.data)


DB = SillyDB()


def rr(*args):

    try:
        location, query = args
    except ValueError:
        location, = args
        query = ''

    key = location, query

    if key in DB:
        logger.debug('Cache Hit: {}/{}'.format(location, query))
        code, text = DB[key]
        if code != 200:
            raise RESTException('[cached] {}'.format(text))
        return text

    logger.debug('Cache Miss: {}/{}'.format(location, query))

    url = urllib.parse.urlunparse(('https', 'rest.coinapi.io/v1', location, '', query, ''))
    headers = {'X-CoinAPI-Key': API_KEY}
    logger.debug('Fetching URL: {}'.format(url))
    response = requests.get(url, headers=headers)

    headers = dict(response.headers)
    for thing in ['Limit', 'Remaining', 'Request-Cost', 'Reset']:
        header_key = 'X-RateLimit-' + thing
        headers.setdefault(header_key, None)

    api_limit_info = """
    X-RateLimit-Limit: {X-RateLimit-Limit}	Request limit allocated in the time window.
    X-RateLimit-Remaining: {X-RateLimit-Remaining}	The number of requests left for the time window.
    X-RateLimit-Request-Cost: {X-RateLimit-Request-Cost}	The number of requests used to generate current HTTP response.
    X-RateLimit-Reset: {X-RateLimit-Reset}	The remaining window before the rate limit resets
    """.format(**headers)
    logger.debug('API Limit Info:' + api_limit_info)

    if response.status_code != 200:
        DB[key] = response.status_code, response.reason
        raise RESTException(response.reason)

    code, text = response.status_code, response.json()
    DB[key] = code, text
    return text

def ws_feed_worker():

    db = redis.StrictRedis(unix_socket_path='/tmp/redis.sock')

    ws = websocket.create_connection("wss://ws.coinapi.io/v1")
    ws.send(json.dumps(dict(
        type='hello',
        apikey=API_KEY,
        heartbeat=True,
        subscribe_data_type = ['trade'],
    )))

    try:
        while True:
          text = ws.recv()
          logger.debug('received: {}'.format(text))
          data = json.loads(text)
          if 'symbol_id' not in data:
              continue
          db.lpush(data['symbol_id'], text)
    finally:
        ws.close()


if __name__ == '__main__':

    assets = rr('assets', '')
    quotes = rr('quotes/current', '')
    symbols = rr('symbols', '')
    foo = rr('symbols', 'filter_symbol_id=BTC')
    usd_in_btc_now = rr('exchangerate/USD/BTC', '')  # how many BTC is one USD
    btc_in_usd_now = rr('exchangerate/BTC/USD', '')  # how many USD is one BTC
    periods = rr('ohlcv/periods', '')
    btc_history_example2 = rr('ohlcv/BITSTAMP_SPOT_BTC_USD/history', 'period_id=1MIN&time_start=2016-01-02T00:00:00')
    latest_trades = rr('trades/latest')
    orderbooks_current = rr('orderbooks/current')
    btc_history_example2_100000 = rr('ohlcv/BITSTAMP_SPOT_BTC_USD/history', 'period_id=1MIN&time_start=2016-01-02T00:00:00&limit=100000')

    points = [x['price_high'] for x in btc_history_example2_100000]

    ws_feed_worker()
