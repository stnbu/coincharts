# -*- mode: python; coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'coincharts.settings'

from mutils.memoize import memoize

from coincharts.db import *

from coincharts import config
config = config.get_config()

symbol_ids = config['history_symbols']

class SymbolIdInfo(object):

    def __init__(self, symbol_id):
        self.symbol_id = symbol_id

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
        return Prices.objects.filter(symbol_id=self.symbol_id)

    @property
    def normalized_price_history(self):
        price_delta = self.max - self.min
        for price in self.history:
            yield (price.price - self.min) / price_delta


class SymbolIdComparison(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    @property
    @memoize
    def start_date_indexes(self):
        indexes = {}
        for symbol_id, data in self.items():
            try:
                indexes[symbol_id] = [s.time for s in data.history].index(self.earliest_common_time)
            except ValueError:
                raise ValueError('Could not find date {} in history of {}'.format(
                    self.earliest_common_time, symbol_id))
        return indexes

    @property
    @memoize
    def earliest_common_time(self):
        return sorted([symbol.history[0].time for symbol in self.values()])[0]

    def normalized_price_history_averages(self):
        normalized_price_history_generators = []
        for symbol_id, data in self.items():
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

    symbol_id_info = SymbolIdComparison()
    for symbol_id in symbol_ids:
        symbol_id_info[symbol_id] = SymbolIdInfo(symbol_id)

    # print('name\t\t\tmin\tmax\t\t\trange')
    # for name, info in symbol_id_info.items():
    #     print(name,
    #           info.min,
    #           info.max, '\t',
    #           info.date_range, sep='\t')

    comparison = SymbolIdComparison(symbol_id_info)

    for p in comparison.normalized_price_history_averages():
        print(p)
