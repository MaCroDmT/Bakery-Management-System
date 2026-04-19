"""
orders/views.py
Handles: Checkout, Order confirmation, Invoice PDF generation,
         Invoice email, Order history, Admin order management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import transaction
from django.conf import settings

from store.models import Cart, CartItem
from .models import Order, OrderItem
from accounts.decorators import admin_required

import io


# ─── Customer Order Views ─────────────────────────────────────────────────────

@login_required
def checkout_view(request):
    """
    Display checkout page with cart summary and shipping form.
    Pre-fills user details.
    """
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related('product').all()

    if not items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')

    # Pre-fill shipping details from user profile
    initial_data = {
        'shipping_name': request.user.get_full_name(),
        'shipping_email': request.user.email,
        'shipping_phone': request.user.phone,
        'shipping_address': request.user.address,
    }

    context = {
        'cart': cart,
        'items': items,
        'initial_data': initial_data,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
@transaction.atomic
def place_order_view(request):
    """
    POST: Convert cart into an Order.
    Steps:
      1. Validate cart is not empty
      2. Create Order with shipping details
      3. Create OrderItems (snapshot product name & price)
      4. Reduce product stock
      5. Clear the cart
      6. Generate PDF invoice
      7. Send invoice by email
      8. Redirect to success page
    """
    if request.method != 'POST':
        return redirect('orders:checkout')

    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related('product').all()

    if not items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')

    # Collect shipping details from POST
    shipping_name = request.POST.get('shipping_name', '').strip()
    shipping_email = request.POST.get('shipping_email', '').strip()
    shipping_phone = request.POST.get('shipping_phone', '').strip()
    shipping_address = request.POST.get('shipping_address', '').strip()
    notes = request.POST.get('notes', '').strip()

    if not all([shipping_name, shipping_email, shipping_phone, shipping_address]):
        messages.error(request, 'Please fill in all shipping details.')
        return redirect('orders:checkout')

    # Calculate total
    total_price = cart.get_total_price()

    # Create the Order
    order = Order.objects.create(
        user=request.user,
        shipping_name=shipping_name,
        shipping_email=shipping_email,
        shipping_phone=shipping_phone,
        shipping_address=shipping_address,
        total_price=total_price,
        notes=notes,
    )

    # Create OrderItems and reduce stock
    for cart_item in items:
        product = cart_item.product
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,          # snapshot
            product_price=product.price,         # snapshot
            quantity=cart_item.quantity,
        )
        # Reduce stock
        if product.stock_quantity >= cart_item.quantity:
            product.stock_quantity -= cart_item.quantity
            product.save()

    # Clear the cart
    items.delete()

    # Generate and send invoice PDF
    try:
        pdf_bytes = generate_invoice_pdf(order)
        send_invoice_email(order, pdf_bytes)
        order.invoice_sent = True
        order.save()
    except Exception as e:
        # Don't fail the order if email fails — just log it
        print(f"Invoice email failed for order {order.invoice_number}: {e}")

    messages.success(request, f'Order placed successfully! Invoice #{order.invoice_number} sent to {shipping_email}.')
    return redirect('orders:order_success', pk=order.pk)


@login_required
def order_success_view(request, pk):
    """Order confirmation page shown after successful checkout."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_history_view(request):
    """Customer's personal order history."""
    orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail_view(request, pk):
    """View a single order's details (customer)."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def download_invoice_view(request, pk):
    """Download PDF invoice for a customer's order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    pdf_bytes = generate_invoice_pdf(order)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{order.invoice_number}.pdf"'
    return response


# ─── Admin Order Views ────────────────────────────────────────────────────────

@admin_required
def admin_order_list_view(request):
    """Admin: View all orders with optional status filter."""
    orders = Order.objects.select_related('user').prefetch_related('items').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'status_filter': status_filter,
    }
    return render(request, 'orders/admin_orders.html', context)


@admin_required
def admin_order_detail_view(request, pk):
    """Admin: View and update a specific order."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f'Order #{order.invoice_number} status updated to "{new_status}".')
            return redirect('orders:admin_order_detail', pk=pk)

    return render(request, 'orders/admin_order_detail.html', {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    })


@admin_required
def admin_download_invoice_view(request, pk):
    """Admin: Download a PDF invoice for any order."""
    order = get_object_or_404(Order, pk=pk)
    pdf_bytes = generate_invoice_pdf(order)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{order.invoice_number}.pdf"'
    return response


# ─── Invoice Helper Functions ─────────────────────────────────────────────────

def generate_invoice_pdf(order):
    """
    Generate a PDF invoice using ReportLab.
    Works on Windows without any extra system libraries.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Colors ──
    green = colors.HexColor('#1a472a')
    light_green = colors.HexColor('#d1e7dd')
    dark = colors.HexColor('#333333')
    grey = colors.HexColor('#666666')

    # ── Custom Styles ──
    title_style = ParagraphStyle('title', fontSize=24, textColor=green, fontName='Helvetica-Bold', spaceAfter=4)
    heading_style = ParagraphStyle('heading', fontSize=11, textColor=green, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('normal', fontSize=10, textColor=dark, fontName='Helvetica')
    small_style = ParagraphStyle('small', fontSize=9, textColor=grey, fontName='Helvetica')
    right_style = ParagraphStyle('right', fontSize=10, alignment=TA_RIGHT, fontName='Helvetica')
    right_bold = ParagraphStyle('right_bold', fontSize=12, alignment=TA_RIGHT, fontName='Helvetica-Bold', textColor=green)

    # ── Header: Company + Invoice Info ──
    header_data = [
        [
            Paragraph('ORBIT FOODS', title_style),
            Paragraph(f'INVOICE', ParagraphStyle('inv', fontSize=20, textColor=green, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ],
        [
            Paragraph('Pure &amp; Healthy Food<br/>Dhaka, Bangladesh<br/>prottoys28@gmail.com', small_style),
            Paragraph(
                f'<b>Invoice #:</b> {order.invoice_number}<br/>'
                f'<b>Date:</b> {order.created_at.strftime("%B %d, %Y")}<br/>'
                f'<b>Status:</b> {order.get_status_display()}',
                ParagraphStyle('inv_detail', fontSize=10, alignment=TA_RIGHT, fontName='Helvetica')
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[9*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=green, spaceAfter=12))

    # ── Billing Info ──
    billing_data = [
        [
            Paragraph('<b>BILL TO:</b>', heading_style),
            Paragraph('<b>FROM:</b>', heading_style),
        ],
        [
            Paragraph(
                f'{order.shipping_name}<br/>'
                f'{order.shipping_email}<br/>'
                f'{order.shipping_phone}<br/>'
                f'{order.shipping_address}',
                normal_style
            ),
            Paragraph(
                'Orbit Foods<br/>'
                'prottoys28@gmail.com<br/>'
                'Dhaka, Bangladesh',
                normal_style
            ),
        ]
    ]
    billing_table = Table(billing_data, colWidths=[8.5*cm, 8.5*cm])
    billing_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(billing_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Items Table ──
    table_data = [['#', 'Product Name', 'Unit Price', 'Qty', 'Subtotal']]
    for i, item in enumerate(order.items.all(), 1):
        table_data.append([
            str(i),
            item.product_name,
            f'Tk {item.product_price}',
            str(item.quantity),
            f'Tk {item.get_subtotal()}',
        ])

    items_table = Table(table_data, colWidths=[1*cm, 8*cm, 3*cm, 2*cm, 3*cm])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0,0), (-1,0), green),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        # Data rows
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('ALIGN', (2,1), (-1,-1), 'CENTER'),
        ('ALIGN', (4,1), (-1,-1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_green]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*cm))

    # ── Totals ──
    totals_data = [
        ['', 'Delivery:', 'Free'],
        ['', 'TOTAL:', f'Tk {order.total_price}'],
    ]
    totals_table = Table(totals_data, colWidths=[9*cm, 4*cm, 4*cm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('FONTNAME', (1,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,1), (-1,1), 13),
        ('TEXTCOLOR', (1,1), (-1,1), green),
        ('LINEABOVE', (1,1), (-1,1), 1.5, green),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(totals_table)

    # ── Notes ──
    if order.notes:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f'<b>Order Notes:</b> {order.notes}', normal_style))

    # ── Footer ──
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=grey))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        'Thank you for shopping with Orbit Foods! | prottoys28@gmail.com | Dhaka, Bangladesh',
        ParagraphStyle('footer', fontSize=9, textColor=grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def send_invoice_email(order, pdf_bytes):
    """
    Sends invoice PDF to:
    1. The customer who placed the order
    2. The company notification email (orbitfoodservice@gmail.com)
    """

    # ── Email 1: To Customer ──────────────────────────────
    customer_subject = f'Orbit Foods — Invoice #{order.invoice_number}'
    customer_body = f"""
Dear {order.shipping_name},

Thank you for your order at Orbit Foods! 🎉

Your order has been placed successfully.
Please find your invoice attached to this email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Invoice Number : {order.invoice_number}
  Order Total    : Tk {order.total_price}
  Status         : {order.get_status_display()}
  Delivery To    : {order.shipping_address}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

We will process your order shortly.
If you have any questions, reply to this email.

Best regards,
Orbit Foods Team
orbitfoodservice@gmail.com
    """

    customer_email = EmailMessage(
        subject=customer_subject,
        body=customer_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.shipping_email],
    )
    customer_email.attach(
        filename=f'invoice-{order.invoice_number}.pdf',
        content=pdf_bytes,
        mimetype='application/pdf'
    )
    customer_email.send(fail_silently=False)

    # ── Email 2: To Company (Notification) ───────────────
    company_notification_email = getattr(
        settings, 'COMPANY_NOTIFICATION_EMAIL', None
    )

    if company_notification_email:
        # Build order items summary
        items_summary = '\n'.join([
            f'  - {item.quantity}x {item.product_name} @ Tk {item.product_price} = Tk {item.get_subtotal()}'
            for item in order.items.all()
        ])

        company_subject = f'🛒 New Order Received — #{order.invoice_number}'
        company_body = f"""
NEW ORDER ALERT!

A new order has been placed on Orbit Foods website.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Invoice #  : {order.invoice_number}
  Date       : {order.created_at.strftime("%B %d, %Y %I:%M %p")}
  Status     : {order.get_status_display()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CUSTOMER DETAILS:
  Name    : {order.shipping_name}
  Email   : {order.shipping_email}
  Phone   : {order.shipping_phone}
  Address : {order.shipping_address}

ITEMS ORDERED:
{items_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ORDER TOTAL: Tk {order.total_price}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please log in to the admin panel to manage this order:
http://127.0.0.1:8000/accounts/admin-dashboard/

        """

        company_email = EmailMessage(
            subject=company_subject,
            body=company_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=company_notification_email if isinstance(company_notification_email, list) else [company_notification_email],
        )
        # Also attach the invoice PDF for company records
        company_email.attach(
            filename=f'invoice-{order.invoice_number}.pdf',
            content=pdf_bytes,
            mimetype='application/pdf'
        )
        company_email.send(fail_silently=True)
