import pytest
from rest_framework import serializers
from subscriptions.serializers import SubscriptionSerializer, PaymentSerializer
from tests.factories import OrganizationFactory
from subscriptions.models import Subscription, Payment, SubscriptionStatus
from uuid import uuid4

@pytest.mark.django_db
class TestSubscriptionSerializer:
    """
    Unit tests for SubscriptionSerializer.
    """

    def test_subscription_serializer_mapping(self):
        """
        Verify that Subscription model fields are correctly mapped to serializer data.
        """
        org = OrganizationFactory()
        subscription = Subscription.objects.create(
            organization=org,
            razorpay_order_id="order_123",
            amount=50000,
            status=SubscriptionStatus.PENDING_PAYMENT
        )
        
        serializer = SubscriptionSerializer(instance=subscription)
        assert serializer.data["razorpay_order_id"] == "order_123"
        assert serializer.data["status"] == SubscriptionStatus.PENDING_PAYMENT
        assert "payments" in serializer.data

@pytest.mark.django_db
class TestPaymentSerializer:
    """
    Unit tests for PaymentSerializer.
    """

    def test_payment_serializer_mapping(self):
        """
        Verify that Payment model fields are correctly mapped to serializer data.
        """
        org = OrganizationFactory()
        sub = Subscription.objects.create(
            organization=org,
            razorpay_order_id="order_123",
            amount=50000
        )
        payment = Payment.objects.create(
            subscription=sub,
            razorpay_payment_id="pay_123",
            amount=50000,
            status="captured"
        )
        
        serializer = PaymentSerializer(instance=payment)
        assert serializer.data["razorpay_payment_id"] == "pay_123"
        assert float(serializer.data["amount"]) == 50000
