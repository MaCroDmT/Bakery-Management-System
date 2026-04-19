"""
accounts/urls.py
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Admin
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('create-admin/', views.create_admin_view, name='create_admin'),
    path('manage-admins/', views.manage_admins_view, name='manage_admins'),
    path('customers/', views.customer_list_view, name='customer_list'),
]
