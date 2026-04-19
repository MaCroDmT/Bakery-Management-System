"""
landing/views.py
Corporate homepage with about, team, contact sections.
"""
from django.shortcuts import render
from store.models import Product


def home_view(request):
    """Main landing page — showcases company info and featured products."""
    featured_products = Product.objects.filter(is_visible=True).order_by('-created_at')[:6]
    return render(request, 'landing/home.html', {'featured_products': featured_products})
