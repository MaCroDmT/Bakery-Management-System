"""
accounts/views.py
Handles: Register, Login, Logout, OTP verify, Create Admin
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import CustomUser, OTPCode
from .forms import CustomerRegistrationForm, LoginForm, OTPVerificationForm, CreateAdminForm
from .decorators import superadmin_required


def register_view(request):
    """Customer registration with OTP email verification."""
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create OTP
            OTPCode.objects.filter(user=user).delete()  # clear old OTPs
            otp = OTPCode.objects.create(
                user=user,
                code=OTPCode.generate_code()
            )

            # Send verification email
            try:
                send_mail(
                    subject='Orbit Foods - Email Verification Code',
                    message=f"""
Hello {user.first_name},

Your verification code for Orbit Foods is:

    {otp.code}

This code expires in 10 minutes.

If you did not register, please ignore this email.

Best regards,
Orbit Foods Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, f'Account created! A 6-digit code was sent to {user.email}.')
            except Exception as e:
                messages.warning(request, f'Account created but email sending failed. Contact support.')

            # Store user email in session for OTP step
            request.session['verify_email'] = user.email
            return redirect('accounts:verify_otp')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    """Verify the OTP code sent to the user's email."""
    email = request.session.get('verify_email')
    if not email:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('accounts:register')

    user = get_object_or_404(CustomUser, email=email)

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            # Get most recent unused OTP for this user
            otp = OTPCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).order_by('-created_at').first()

            if otp is None:
                messages.error(request, 'Invalid verification code.')
            elif otp.is_expired():
                messages.error(request, 'This code has expired. Please request a new one.')
            else:
                # Mark OTP used and activate user
                otp.is_used = True
                otp.save()
                user.is_active = True
                user.is_verified = True
                user.save()

                # Clear session
                del request.session['verify_email']

                messages.success(request, 'Email verified! You can now log in.')
                return redirect('accounts:login')
    else:
        form = OTPVerificationForm()

    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': email})


def resend_otp_view(request):
    """Resend OTP to the user's email."""
    email = request.session.get('verify_email')
    if not email:
        return redirect('accounts:register')

    user = get_object_or_404(CustomUser, email=email)

    # Delete old OTPs and create fresh one
    OTPCode.objects.filter(user=user).delete()
    otp = OTPCode.objects.create(user=user, code=OTPCode.generate_code())

    try:
        send_mail(
            subject='Orbit Foods - New Verification Code',
            message=f'Your new verification code is: {otp.code}\nExpires in 10 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        messages.success(request, f'New code sent to {user.email}.')
    except Exception:
        messages.error(request, 'Failed to send email. Please try again.')

    return redirect('accounts:verify_otp')


def login_view(request):
    """Customer and Admin login view."""
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_verified:
                request.session['verify_email'] = user.email
                messages.warning(request, 'Please verify your email first.')
                return redirect('accounts:verify_otp')
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')

            # Redirect admins to admin dashboard
            if user.is_admin:
                return redirect('accounts:admin_dashboard')
            return redirect('store:product_list')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout and redirect to homepage."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing:home')


@login_required
def profile_view(request):
    """Customer profile page."""
    return render(request, 'accounts/profile.html', {'user': request.user})


# ─── Admin Views ─────────────────────────────────────────────────────────────

@login_required
def admin_dashboard_view(request):
    """Main admin dashboard - accessible by admin and superadmin."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('store:product_list')

    from store.models import Product
    from orders.models import Order

    context = {
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'total_customers': CustomUser.objects.filter(role='customer').count(),
        'recent_orders': Order.objects.order_by('-created_at')[:5],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
def create_admin_view(request):
    """Only superadmin can create new admins."""
    if not request.user.is_superadmin:
        messages.error(request, 'Only the Super Administrator can create admin accounts.')
        return redirect('accounts:admin_dashboard')

    if request.method == 'POST':
        form = CreateAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New administrator account created successfully.')
            return redirect('accounts:manage_admins')
    else:
        form = CreateAdminForm()

    return render(request, 'accounts/create_admin.html', {'form': form})


@login_required
def manage_admins_view(request):
    """List all admins - superadmin only."""
    if not request.user.is_superadmin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:admin_dashboard')

    admins = CustomUser.objects.filter(role__in=['admin', 'superadmin']).order_by('date_joined')
    return render(request, 'accounts/manage_admins.html', {'admins': admins})

@login_required
def customer_list_view(request):
    """Admin: View all registered customers."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('store:product_list')

    customers = CustomUser.objects.filter(role='customer').order_by('-date_joined')
    return render(request, 'accounts/customer_list.html', {'customers': customers})
