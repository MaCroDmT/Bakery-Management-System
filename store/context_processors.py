"""
store/context_processors.py
Makes cart_count available in every template automatically.
Added to TEMPLATES context_processors in settings.py.
"""


def cart_count(request):
    """Return the number of distinct items in the user's cart."""
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            return {'cart_count': cart.items.count()}
        except Exception:
            return {'cart_count': 0}
    return {'cart_count': 0}
