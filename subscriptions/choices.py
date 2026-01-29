from django.db import models

class SubscriptionStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
    ACTIVE = "ACTIVE", "Active"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class PlanType(models.TextChoices):
    LIFETIME = "LIFETIME", "Lifetime Premium"


class PaymentStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    CAPTURED = "CAPTURED", "Captured"
    FAILED = "FAILED", "Failed"
