from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from .models import Prices

from dateutil.parser import parse as parse_dt
import time

import svg_graph

def index(request, symbol_id):
    prices = Prices.objects.filter(symbol_id=symbol_id)[:100]

    # these make no sense. testing.
    x_labels = svg_graph.GraphLabel('Year',
                          values=(2008, 2009, 2010, 2011, 2012),
                          padding=100)

    y_labels = svg_graph.GraphLabel('Price',
                          values=(0, 5, 10, 15),
                          padding=100,
                          omit_zeroith=True)

    def string_to_epoch(string):
        return time.mktime(parse_dt(string).timetuple())

    def prices_gen(prices):
        x = []
        for p in prices:
            x.append((string_to_epoch(p.time), int(p.price)))
        return x

    xyz = prices_gen(prices)
    print('-'*100)
    print(len(xyz))
    print('-'*100)

    graph = svg_graph.LineGraph(
        'Look at This Graph',
        height=580,
        width=700,
        points=xyz,
        labels=[x_labels, y_labels]
    )

    context = {
        'graph': graph,
        'prices': prices,
    }
    return render(request, 'coincharts/index.html', context)
