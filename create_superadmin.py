"""
create_superadmin.py
Run this ONCE after migrations to create the default superadmin account.

Usage:
    python create_superadmin.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orbit_foods.settings')
django.setup()

from accounts.models import CustomUser

EMAIL = 'prottoys28@gmail.com'
PASSWORD = 'Wemethey@4'
FIRST_NAME = 'Super'
LAST_NAME = 'Admin'

if CustomUser.objects.filter(email=EMAIL).exists():
    print(f'[!] Superadmin with email "{EMAIL}" already exists. Skipping.')
else:
    user = CustomUser.objects.create_superuser(
        email=EMAIL,
        password=PASSWORD,
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
    )
    print(f'[✓] Superadmin created successfully!')
    print(f'    Email    : {EMAIL}')
    print(f'    Password : {PASSWORD}')
    print(f'    Role     : {user.role}')
