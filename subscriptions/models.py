import uuid
from django.db import models
from users.models import Organization
from subscriptions.choices import SubscriptionStatus, PlanType, PaymentStatus

class Subscription(models.Model):
    """
    One subscription per organization (lifetime plan).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.LIFETIME
    )
    
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING_PAYMENT,
        db_index=True
    )
    
    # Razorpay identifiers
    razorpay_order_id = models.CharField(max_length=100, unique=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # In rupees
    currency = models.CharField(max_length=3, default="INR")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "subscriptions"
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan_type} ({self.status})"


class Payment(models.Model):
    """
    Tracks individual payment transactions.
    Links to subscription for audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    
    # Razorpay identifiers
    razorpay_order_id = models.CharField(max_length=100, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True
    )
    
    # Payment method (card, upi, netbanking, etc.)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    
    # Error tracking
    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_description = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
    
    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status}"


class WebhookEvent(models.Model):
    """
    Stores raw webhook events from Razorpay.
    Ensures idempotency and provides audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Razorpay event identifier (for idempotency)
    event_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Event type (payment.captured, payment.failed, etc.)
    event_type = models.CharField(max_length=50, db_index=True)
    
    # Raw payload from Razorpay
    payload = models.JSONField()
    
    # Webhook signature for verification
    signature = models.CharField(max_length=255)
    
    # Processing status
    is_verified = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    processing_error = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "webhook_events"
        indexes = [
            models.Index(fields=["is_processed", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
