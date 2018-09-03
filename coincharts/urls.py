
from django.urls import path
from . import views

urlpatterns = [
    path('<str:symbol_id>/', views.index, name='index'),
]
