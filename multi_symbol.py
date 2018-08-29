
import datetime
from dateutil.parser import parse as parse_dt
import base


class PriceHistoryComparison(object):

    def __init__(self, data):
        self.data = data
        # FIXME
        self.len = len(min(data.values(), key=len))
        self.symbols = list(data.keys())

    def thing(self):
        for i in range(0, self.len):
            columns = []
            dt = self.data[self.symbols[0]][i][0]
            columns = [dt]
            for key in self.symbols:
                columns.append(self.data[key][1][1])
            yield columns


if __name__ == '__main__':

    dt_text = '2018-01-09T17:00:00.0000000Z'
    data = {}
    for key in 'BTC', 'ETH', 'XRP':
        ps = base.PriceSeries('BITSTAMP_SPOT_{}_USD'.format(key), create_store=False)
        data[key] = ps.get_prices_since(dt_text)

    phc = PriceHistoryComparison(data)
    phc.thing()
