from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from .models import Prices

from dateutil.parser import parse as parse_dt
import time
from coincharts import config
from coincharts.data import SymbolComparison, SymbolInfo

config = config.get_config()

import svg_graph

def index(request):

    symbols = config['history_symbols']
    comparison = SymbolComparison()
    for symbol in symbols:
        comparison[symbol] = SymbolInfo(symbol, length=967)
    history_generator = comparison.normalized_history_averages()

    graph = svg_graph.LineGraph(
        title='Price history averages',
        height=580,
        width=1200,
        points=history_generator,
        length=comparison.length
    )

    context = {
        'graph': graph.to_xml(),
    }
    return render(request, 'coincharts/index.html', context)
