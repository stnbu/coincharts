from django.shortcuts import render

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
#from .models import Page, Content

def page(request, current_page_name):
    context = {
    }
    return render(request, 'main/index.html', context)
