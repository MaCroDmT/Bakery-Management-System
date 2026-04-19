"""
URL Configuration for Orbit Foods - Main urls.py
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing page (homepage)
    path('', include('landing.urls')),

    # Accounts: register, login, logout, email verify
    path('accounts/', include('accounts.urls')),

    # Store: products, cart
    path('store/', include('store.urls')),

    # Orders: checkout, history, invoice
    path('orders/', include('orders.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
