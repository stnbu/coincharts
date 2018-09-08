# -*- mode: python; coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'coincharts.settings'
from dateutil.parser import parse as parse_dt

from mutils.memoize import memoize

from coincharts.db import *
from coincharts.models import THE_DATETIME_FIELD, THE_PRICE_FIELD

from coincharts import config
config = config.get_config()

date_format_template = '%Y-%m-%dT%H:%M:%S.%f0Z'  # magic

class SymbolInfo(object):

    def __init__(self, symbol, since=None):
        self.symbol = symbol
        self.since = since

    @property
    @memoize
    def min(self):
        return min([s.price for s in self.history])

    @property
    @memoize
    def max(self):
        return max([s.price for s in self.history])

    @property
    @memoize
    def history(self):
        kwargs = dict(symbol=self.symbol)
        if self.since is not None:
            dt__gte = '{}__gte'.format(THE_DATETIME_FIELD)  # `@property` name mangling not supported
            kwargs[dt__gte] = self.since

        history = Prices.objects.filter(**kwargs)
        self.length = len(history)
        return history

    @property
    def normalized_history(self):
        price_delta = self.max - self.min
        for record in self.history:
            yield parse_dt(record.dt).timestamp(), (record.price - self.min) / price_delta


class SymbolComparison(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def normalized_history_averages(self):
        normalized_history_generators = []
        for symbol, data in self.items():
            normalized_history_generators.append(
                data.normalized_history
            )
        num_prices = len(self)
        while True:
            prices = set()
            for gen in normalized_history_generators:
                try:
                    point = gen.__next__()
                    # this means we end up using the dt value of the last point we get.
                    # this shouldn't matter, since they are *supposed* to all be the same.
                    # the validation of this and other things should be implemented.
                    dt, price = point
                    prices.add(price)
                except StopIteration:
                    return
            yield dt, sum(prices) / num_prices

if __name__ == '__main__':

    symbols = config['history_symbols']
    comparison = SymbolComparison()
    for symbol in symbols:
        comparison[symbol] = SymbolInfo(symbol)

    for p in comparison.normalized_history_averages():
        print(p)
