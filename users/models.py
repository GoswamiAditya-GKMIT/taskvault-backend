import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.choices import UserRoleChoices


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False, db_index=True)  # Premium subscription flag

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True , blank=True)

    class Meta:
        db_table = "organizations"

    def __str__(self):
        return self.name
    

class User(AbstractUser):
    id = models.UUIDField(primary_key=True , default= uuid.uuid4 , editable=False)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )

    email = models.EmailField(unique=True)

    role = models.CharField(
            max_length = 20,
            choices=UserRoleChoices.choices,
            default=UserRoleChoices.USER
    )

    is_email_verified = models.BooleanField(default=False)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True , blank=True)

    DELETED_BY_CHOICES = (
        ('self', 'Self'),
        ('admin', 'Admin'),
    )
    deleted_by = models.CharField(max_length=10, choices=DELETED_BY_CHOICES, null=True, blank=True)

    REQUIRED_FIELDS = ["email"]
    USERNAME_FIELD = "username"

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

