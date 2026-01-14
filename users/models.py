import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.choices import UserRoleChoices

# Create your models here.

class User(AbstractUser):
    id = models.UUIDField(primary_key=True , default= uuid.uuid4 , editable=False)
    email = models.EmailField(unique=True)

    role = models.CharField(
            max_length = 10,
            choices=UserRoleChoices.choices,
            default=UserRoleChoices.USER
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True , blank=True)

    REQUIRED_FIELDS = ["email"]
    USERNAME_FIELD = "username"

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["created_at"]),
        ]









