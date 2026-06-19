# tracker/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('profile/', views.profile_view, name='profile'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('security-question/', views.security_question_view, name='security_question'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
]