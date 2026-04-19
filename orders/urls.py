"""
orders/urls.py
"""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Customer
    path('checkout/', views.checkout_view, name='checkout'),
    path('place/', views.place_order_view, name='place_order'),
    path('success/<int:pk>/', views.order_success_view, name='order_success'),
    path('history/', views.order_history_view, name='order_history'),
    path('detail/<int:pk>/', views.order_detail_view, name='order_detail'),
    path('invoice/<int:pk>/download/', views.download_invoice_view, name='download_invoice'),

    # Admin
    path('admin/orders/', views.admin_order_list_view, name='admin_orders'),
    path('admin/orders/<int:pk>/', views.admin_order_detail_view, name='admin_order_detail'),
    path('admin/orders/<int:pk>/invoice/', views.admin_download_invoice_view, name='admin_download_invoice'),
]
