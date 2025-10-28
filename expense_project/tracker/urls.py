# tracker/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), # Handles the root URL (page rendering)
    path('api/expenses/', views.api_expenses, name='api_expenses'), # Handles data API
]