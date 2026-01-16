# core/choices.py
from django.db import models

class UserRoleChoices(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    TENANT_ADMIN = "TENANT_ADMIN", "Tenant Admin"
    USER = "USER", "User"


class TaskStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"

class TaskPriorityChoices(models.TextChoices):
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"



