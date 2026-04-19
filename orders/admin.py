"""
orders/admin.py
"""
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'product_price', 'quantity', 'get_subtotal')

    def get_subtotal(self, obj):
        return f"৳{obj.get_subtotal()}"
    get_subtotal.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'shipping_name', 'total_price', 'status', 'invoice_sent', 'created_at')
    list_filter = ('status', 'invoice_sent')
    search_fields = ('invoice_number', 'shipping_name', 'shipping_email')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
