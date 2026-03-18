import os
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Organization
from rest_framework_simplejwt.tokens import RefreshToken
from core.choices import UserRoleChoices

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates 10 sample users and their access tokens for Locust load testing.'

    def handle(self, *args, **options):
        # 1. Ensure a Load Test Organization exists
        org, created = Organization.objects.get_or_create(
            name="Load Test Org",
            defaults={"is_premium": True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Load Test Organization: {org.name}'))

        tokens = []
        
        # 2. Create 10 Load Test Users
        for i in range(1, 11):
            username = f'loadtest_user_{i}'
            email = f'loadtest_{i}@example.com'
            password = 'password123'
            
            user, u_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "organization": org,
                    "role": UserRoleChoices.USER,
                    "is_email_verified": True
                }
            )
            
            if u_created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'Created User: {username}')
            
            # 3. Generate Access Token
            refresh = RefreshToken.for_user(user)
            tokens.append(str(refresh.access_token))

        # 4. Save tokens to file for Locust
        token_file = 'locust_tokens.txt'
        with open(token_file, 'w') as f:
            for token in tokens:
                f.write(f"{token}\n")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated 10 tokens in {token_file}'))
