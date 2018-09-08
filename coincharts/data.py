# -*- mode: python; coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'coincharts.settings'
from dateutil.parser import parse as parse_dt

from mutils.memoize import memoize

from coincharts.db import *
from coincharts.models import THE_DATETIME_FIELD, THE_PRICE_FIELD

from coincharts import config
config = config.get_config()


class SymbolInfo(object):

    def __init__(self, symbol, length, since=None):
        self.symbol = symbol
        self.length = length  # this is set below when we access the "history". Being as lazy as possible.
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

    @property
    def length(self):
        # `self.length` has to be a calculated value, we may be truncating other symbol histories
        # so we're only dealing with time periods where they all overlap (are present).
        # So it's up to me* to set self.length as soon as practical.
        # For now we'll just grab an arbitrary symbol and use its lenght attribute
        return list(self.values())[0].length  # <-- only a few symbols. not expensive.

    def normalized_history_averages(self):
        normalized_history_generators = []
        for symbol, data in self.items():
            normalized_history_generators.append(
                data.normalized_history
            )
        num_prices = len(self)
        while True:
            prices = []
            for gen in normalized_history_generators:
                try:
                    point = gen.__next__()
                    # this means we end up using the dt value of the last point we get.
                    # this shouldn't matter, since they are *supposed* to all be the same.
                    # the validation of this and other things should be implemented.
                    dt, price = point
                    prices.append(price)
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
