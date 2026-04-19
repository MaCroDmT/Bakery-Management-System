"""
store/views.py
Handles: Product listing, product detail, cart add/update/remove, admin product CRUD
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import Product, Category, Cart, CartItem
from .forms import ProductForm, CategoryForm, AddToCartForm
from accounts.decorators import admin_required


# ─── Public Store Views ───────────────────────────────────────────────────────

def product_list_view(request):
    """Main store page — shows all visible products with optional category filter."""
    products = Product.objects.filter(is_visible=True).select_related('category')
    categories = Category.objects.all()

    selected_category = request.GET.get('category')
    search_query = request.GET.get('q', '')

    if selected_category:
        products = products.filter(category__slug=selected_category)

    if search_query:
        products = products.filter(name__icontains=search_query)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
    }
    return render(request, 'store/product_list.html', context)


def product_detail_view(request, slug):
    """Individual product detail page."""
    product = get_object_or_404(Product, slug=slug, is_visible=True)
    form = AddToCartForm()
    return render(request, 'store/product_detail.html', {'product': product, 'form': form})


# ─── Cart Views ───────────────────────────────────────────────────────────────

@login_required
def cart_view(request):
    """Display the current user's shopping cart."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()
    return render(request, 'store/cart.html', {'cart': cart, 'items': items})


@login_required
def add_to_cart_view(request, product_id):
    """Add a product to cart or increase its quantity."""
    product = get_object_or_404(Product, id=product_id, is_visible=True)

    if not product.is_in_stock:
        messages.error(request, f'"{product.name}" is currently out of stock.')
        return redirect('store:product_detail', slug=product.slug)

    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        quantity = 1

    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            # Product already in cart — increase quantity
            cart_item.quantity += quantity
            cart_item.save()

    messages.success(request, f'"{product.name}" added to your cart.')
    return redirect('store:cart')


@login_required
def update_cart_view(request, item_id):
    """Update the quantity of a cart item."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))

    if quantity < 1:
        cart_item.delete()
        messages.info(request, 'Item removed from cart.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Cart updated.')

    return redirect('store:cart')


@login_required
def remove_from_cart_view(request, item_id):
    """Remove a specific item from the cart."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f'"{product_name}" removed from cart.')
    return redirect('store:cart')


# ─── Admin Product Management Views ──────────────────────────────────────────

@admin_required
def admin_product_list_view(request):
    """Admin: View all products (visible and hidden)."""
    products = Product.objects.select_related('category').all()
    return render(request, 'store/admin_products.html', {'products': products})


@admin_required
def admin_add_product_view(request):
    """Admin: Add a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('store:admin_products')
    else:
        form = ProductForm()
    return render(request, 'store/admin_product_form.html', {'form': form, 'action': 'Add'})


@admin_required
def admin_edit_product_view(request, pk):
    """Admin: Edit an existing product."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('store:admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/admin_product_form.html', {'form': form, 'action': 'Edit', 'product': product})


@admin_required
def admin_delete_product_view(request, pk):
    """Admin: Delete a product (POST only)."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
    return redirect('store:admin_products')


@admin_required
def admin_toggle_visibility_view(request, pk):
    """Admin: Toggle a product's visibility on/off."""
    product = get_object_or_404(Product, pk=pk)
    product.is_visible = not product.is_visible
    product.save()
    status = 'visible' if product.is_visible else 'hidden'
    messages.success(request, f'"{product.name}" is now {status}.')
    return redirect('store:admin_products')


@admin_required
def admin_category_list_view(request):
    """Admin: Manage product categories."""
    categories = Category.objects.all()
    form = CategoryForm()

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created.')
            return redirect('store:admin_categories')

    return render(request, 'store/admin_categories.html', {'categories': categories, 'form': form})
