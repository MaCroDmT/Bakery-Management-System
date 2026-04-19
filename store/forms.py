"""
store/forms.py
Forms for product management (admin) and cart operations.
"""

from django import forms
from .models import Product, Category


class ProductForm(forms.ModelForm):
    """Form for admin to create or update products."""
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'image', 'stock_quantity', 'is_visible']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Product description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    """Form for admin to create product categories."""
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AddToCartForm(forms.Form):
    """Simple form to add a product to cart with a quantity."""
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 80px;',
            'min': '1'
        })
    )
