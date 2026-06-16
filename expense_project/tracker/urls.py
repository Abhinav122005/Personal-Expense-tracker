# tracker/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('api/expenses/', views.api_expenses, name='api_expenses'), 
    path('api/expenses/<int:expense_id>/', views.api_expense_detail, name='api_expense_detail'),
    path('api/analytics/', views.api_analytics, name='api_analytics'), 
    path('api/budget/', views.api_budget, name='api_budget'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]