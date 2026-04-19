"""
accounts/models.py
Custom User model with email-based OTP verification.
Relationships:
  - CustomUser is the AUTH_USER_MODEL used across all apps
  - OTPCode links to CustomUser (one-to-one per active OTP)
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import random
import string


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser: email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', 'superadmin')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model.
    Roles: customer | admin | superadmin
    Email verification required for customers to log in.
    """
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Administrator'),
        ('superadmin', 'Super Administrator'),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    is_active = models.BooleanField(default=False)   # False until email verified
    is_verified = models.BooleanField(default=False)  # Email verified flag
    is_staff = models.BooleanField(default=False)     # Django admin access

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        db_table = 'accounts_customuser'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role in ('admin', 'superadmin')

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'


class OTPCode(models.Model):
    """
    One-Time Password for email verification.
    Relationship: ForeignKey to CustomUser (one user can have one active OTP).
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='otp_codes'
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_otpcode'

    def __str__(self):
        return f"OTP for {self.user.email} - {self.code}"

    @staticmethod
    def generate_code():
        """Generate a 6-digit numeric OTP."""
        return ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        """Check if OTP is older than 10 minutes."""
        from django.conf import settings
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        expiry_time = self.created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() > expiry_time
