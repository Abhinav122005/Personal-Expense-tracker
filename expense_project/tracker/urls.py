# tracker/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]