from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from .models import Prices

def index(request, symbol_id):
    prices = Prices.objects.filter(symbol_id=symbol_id)[:100]

    context = {
        'prices': prices,
    }
    return render(request, 'coincharts/index.html', context)
