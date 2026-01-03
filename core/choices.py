# core/choices.py
from django.db import models

class UserRoleChoices(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    USER = "USER", "User"

class TaskStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"

class TaskPriorityChoices(models.TextChoices):
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"



