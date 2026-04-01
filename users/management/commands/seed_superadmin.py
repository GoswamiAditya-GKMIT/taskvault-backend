from django.core.management.base import BaseCommand
import os
from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with a Super Admin user if one does not exist.'

    def handle(self, *args, **options):
        # Configuration from environment or defaults
        ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME")
        ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
        ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")

        if not all([ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD]):
            self.stdout.write(self.style.WARNING("Missing environment variables: SUPER_ADMIN_USERNAME, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD. Skipping."))
            return

        # Check if a Super Admin already exists to prevent duplicates
        if User.objects.filter(role=UserRoleChoices.SUPER_ADMIN).exists():
            self.stdout.write(self.style.WARNING("SUPER_ADMIN already exists. Skipping creation."))
            return

        self.stdout.write(f"Attempting to create SUPER_ADMIN: {ADMIN_USERNAME}...")

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

            self.stdout.write(self.style.SUCCESS("SUPER_ADMIN created successfully."))
            self.stdout.write(f"Username: {ADMIN_USERNAME}")
            self.stdout.write(f"Email: {ADMIN_EMAIL}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred during seeding: {e}"))
