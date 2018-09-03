from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from .models import Prices

def index(request):
    prices = Prices.objects.all()[:100]
    context = {
        'prices': prices,
    }
    return render(request, 'coincharts/index.html', context)
