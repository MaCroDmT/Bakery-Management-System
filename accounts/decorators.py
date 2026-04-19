"""
accounts/decorators.py
Custom permission decorators for admin-only views.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """Decorator: only admin or superadmin can access the view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_admin:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('store:product_list')
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    """Decorator: only superadmin can access the view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_superadmin:
            messages.error(request, 'Only the Super Administrator can perform this action.')
            return redirect('accounts:admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
