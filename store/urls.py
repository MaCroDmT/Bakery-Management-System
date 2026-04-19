"""
store/urls.py
"""
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Public store
    path('', views.product_list_view, name='product_list'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_view, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),

    # Admin product management
    path('admin/products/', views.admin_product_list_view, name='admin_products'),
    path('admin/products/add/', views.admin_add_product_view, name='admin_add_product'),
    path('admin/products/edit/<int:pk>/', views.admin_edit_product_view, name='admin_edit_product'),
    path('admin/products/delete/<int:pk>/', views.admin_delete_product_view, name='admin_delete_product'),
    path('admin/products/toggle/<int:pk>/', views.admin_toggle_visibility_view, name='admin_toggle_product'),
    path('admin/categories/', views.admin_category_list_view, name='admin_categories'),
]
