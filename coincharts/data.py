# -*- mode: python; coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'coincharts.settings'

from mutils.memoize import memoize

from coincharts.db import *

from coincharts import config
config = config.get_config()

symbols = config['history_symbols']

class SymbolInfo(object):

    def __init__(self, symbol):
        self.symbol = symbol

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
        return Prices.objects.filter(symbol=self.symbol)

    @property
    def normalized_history(self):
        price_delta = self.max - self.min
        for record in self.history:
            yield record.dt, (record.price - self.min) / price_delta


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

    comparison = SymbolComparison()
    for symbol in symbols:
        comparison[symbol] = SymbolInfo(symbol)

    for p in comparison.normalized_history_averages():
        print(p)
