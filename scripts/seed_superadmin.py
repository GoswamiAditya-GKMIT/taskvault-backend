"""
Admin seeding script for TaskVault
"""

import os
from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices

User = get_user_model()

# Configuration from environment or defaults
ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME")
ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")


def run():
    # Check if a Super Admin already exists to prevent duplicates
    if User.objects.filter(role=UserRoleChoices.SUPER_ADMIN).exists():
        print("SUPER_ADMIN already exists. Skipping creation.")
        return

    print(f"Attempting to create SUPER_ADMIN: {ADMIN_USERNAME}...")

    try:
        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            first_name="Super",
            last_name="Admin",
            role=UserRoleChoices.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
            is_email_verified=True,
            is_active=True,
            organization=None,
        )

        admin.set_password(ADMIN_PASSWORD)
        admin.save()

        print("SUPER_ADMIN created successfully.")
        print(f"Username: {ADMIN_USERNAME}")
        print(f"Email: {ADMIN_EMAIL}")
        
    except Exception as e:
        print(f"An error occurred during seeding: {e}")


run()