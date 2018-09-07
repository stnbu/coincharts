
from django.urls import path
from . import views

urlpatterns = [
    path('<str:symbol>/', views.index, name='index'),
]
