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

    def normalize_price(self, price):
        return (price - self.min) / (self.max - self.min)

    def normalized_price_history(self):
        return map(self.normalize_price, self.history)

    @property
    @memoize
    def date_range(self):
        start = self.history[0].time
        end = self.history[len(self.history)-1].time
        return start, end

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
    def normalized_price_history(self):
        price_delta = self.max - self.min
        for price in self.history:
            yield (price.price - self.min) / price_delta


class SymbolComparison(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    @property
    @memoize
    def start_date_indexes(self):
        indexes = {}
        for symbol, data in self.items():
            try:
                indexes[symbol] = [s.time for s in data.history].index(self.earliest_common_time)
            except ValueError:
                raise ValueError('Could not find date {} in history of {}'.format(
                    self.earliest_common_time, symbol))
        return indexes

    @property
    @memoize
    def earliest_common_time(self):
        return sorted([symbol.history[0].time for symbol in self.values()])[0]

    def normalized_price_history_averages(self):
        normalized_price_history_generators = []
        for symbol, data in self.items():
            normalized_price_history_generators.append(
                data.normalized_price_history
            )
        num_prices = len(self)

        while True:
            prices = []
            for gen in normalized_price_history_generators:
                try:
                    prices.append(gen.__next__())
                except StopIteration:
                    return
                yield sum(prices) / num_prices

if __name__ == '__main__':

    symbol_info = SymbolComparison()
    for symbol in symbols:
        symbol_info[symbol] = SymbolInfo(symbol)

    # print('name\t\t\tmin\tmax\t\t\trange')
    # for name, info in symbol_info.items():
    #     print(name,
    #           info.min,
    #           info.max, '\t',
    #           info.date_range, sep='\t')

    comparison = SymbolComparison(symbol_info)

    for p in comparison.normalized_price_history_averages():
        print(p)
