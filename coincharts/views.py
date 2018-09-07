from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from .models import Prices

from dateutil.parser import parse as parse_dt
import time

import svg_graph

def index(request, symbol):
    prices = Prices.objects.filter(symbol=symbol)[:1000]

    def string_to_epoch(string):
        return time.mktime(parse_dt(string).timetuple())

    def prices_gen(prices):
        x = []
        for p in prices:
            x.append((p.time, int(p.price)))
        return x

    title = '{} from {} to {}'.format(
        symbol,
        prices[0].time,
        prices[len(prices)-1].time,  # "negative indexing is not supported"
    )

    graph = svg_graph.LineGraph(
        title,
        height=580,
        width=1200,
        points=prices_gen(prices),
        linear_x=True
    )

    context = {
        'graph': graph,
        'prices': prices,
    }
    return render(request, 'coincharts/index.html', context)
