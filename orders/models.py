"""
orders/models.py
Models: Order, OrderItem

Relationships:
  - Order → CustomUser (ForeignKey: one user can have many orders)
  - OrderItem → Order (ForeignKey: one order has many items)
  - OrderItem → Product (ForeignKey: snapshot of product at time of order)
"""

from django.db import models
from django.conf import settings
from store.models import Product
import uuid


class Order(models.Model):
    """
    A confirmed customer order.
    Created when the user checks out from the cart.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Shipping address snapshot at time of order
    shipping_name = models.CharField(max_length=200)
    shipping_email = models.EmailField()
    shipping_phone = models.CharField(max_length=20)
    shipping_address = models.TextField()

    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    invoice_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.invoice_number} — {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_invoice_number():
        """Generate a unique invoice number like ORB-20240101-XXXX."""
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"ORB-{date_str}-{unique_part}"

    def get_status_badge_color(self):
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')


class OrderItem(models.Model):
    """
    A single product line within an order.
    Price is stored as a snapshot — won't change if product price changes later.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    product_name = models.CharField(max_length=200)   # snapshot
    product_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = 'orders_orderitem'

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    def get_subtotal(self):
        return self.product_price * self.quantity
