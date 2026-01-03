"""
Admin seeding script for TaskVault

"""

from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices

User = get_user_model()

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin@123"


def run():
    if User.objects.filter(username=ADMIN_USERNAME).exists():
        print("Admin user already exists. Skipping creation.")
        return

    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        first_name="System",
        last_name="Administrator",
        role=UserRoleChoices.ADMIN,
        is_staff=True,        
        is_superuser=True,   
    )

    admin.set_password(ADMIN_PASSWORD)
    admin.save()

    print("Admin user created successfully.")
    print(f"Username: {ADMIN_USERNAME}")
    print(f"Email: {ADMIN_EMAIL}")


run()
