# -*- mode: python; coding: utf-8 -*-
""" Having fun with https://www.coinapi.io/
"""

import requests
import dbm
import collections
import json
import urllib


class RESTException(Exception):
    pass


API_KEY = open('API_KEY').read().strip()
URL_BASE = 'https://rest.coinapi.io/v1/'
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

    location, query = args

    if args in DB:
        code, text = DB[args]
        if code != 200:
            raise RESTException('[cached] {}'.format(text))
        return text

    url = URL_BASE + location
    headers = {'X-CoinAPI-Key': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        DB[args] = response.status_code, response.reason
        raise RESTException(response.reason)

    code, text = response.status_code, response.json()
    DB[args] = code, text
    return text


if __name__ == '__main__':

    rr('quotes/current', '')
