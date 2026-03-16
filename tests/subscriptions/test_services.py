import pytest
from django.conf import settings
from subscriptions.services import create_order
from subscriptions.models import Subscription, SubscriptionStatus, Payment, PaymentStatus
from core.choices import UserRoleChoices

@pytest.mark.django_db
class TestSubscriptionService:
    """
    Test suite for subscription service layer logic.
    """

    def test_create_order_service_success(self, active_organization, mock_razorpay_client):
        """
        Verify that create_order service correctly interacts with Razorpay 
        and saves records to the database.
        """ 
        # Configure the mock to return a fake razorpay order
        fake_order_id = "order_service_123"
        mock_razorpay_client.return_value.order.create.return_value = {
            'id': fake_order_id,
            'amount': 100000,
            'currency': 'INR',
            'status': 'created'
        }

        # Call the service
        subscription = create_order(active_organization)

        # Assertions: Razorpay interaction
        mock_razorpay_client.return_value.order.create.assert_called_once()
        
        # Assertions: Database state
        assert subscription.razorpay_order_id == fake_order_id
        assert subscription.status == SubscriptionStatus.PENDING_PAYMENT
        assert subscription.organization == active_organization
        
        # Check if Payment record was created
        payment = Payment.objects.filter(razorpay_order_id=fake_order_id).first()
        assert payment is not None
        assert payment.subscription == subscription
        assert payment.status == PaymentStatus.CREATED

    def test_create_order_already_active_fails(self, active_organization, mock_razorpay_client):
        """
        Verify that create_order fails if an active subscription already exists.
        """
        # Create an existing active subscription
        Subscription.objects.create(
            organization=active_organization,
            status=SubscriptionStatus.ACTIVE,
            razorpay_order_id="active_order_id",
            amount=settings.PREMIUM_PLAN_AMOUNT / 100,
            currency="INR"
        )

        # Attempt to create another one should raise ValueError
        with pytest.raises(ValueError, match="Organization already has an active premium subscription"):
            create_order(active_organization)
        
        # Razorpay should NOT be called
        mock_razorpay_client.return_value.order.create.assert_not_called()

    def test_activate_subscription_success(self, active_organization):
        """
        Verify that activate_subscription_atomic correctly flips the is_premium flag
        and updates subscription/payment status.
        """
        from subscriptions.services import activate_subscription_atomic
        
        # 1. Setup: Create a pending subscription and a payment record
        order_id = "test_order_activate_123"
        subscription = Subscription.objects.create(
            organization=active_organization,
            status=SubscriptionStatus.PENDING_PAYMENT,
            razorpay_order_id=order_id,
            amount=1000,
            currency="INR"
        )
        Payment.objects.create(
            subscription=subscription,
            razorpay_order_id=order_id,
            amount=1000,
            currency="INR",
            status=PaymentStatus.CREATED
        )

        # 2. Action: Activate it
        payment_id = "pay_test_456"
        signature = "sig_test_789"
        activate_subscription_atomic(subscription, payment_id, signature)

        # 3. Assertions
        # Refresh from DB
        subscription.refresh_from_db()
        active_organization.refresh_from_db()
        payment = Payment.objects.get(razorpay_order_id=order_id)

        assert active_organization.is_premium is True
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.razorpay_payment_id == payment_id
        assert subscription.razorpay_signature == signature
        assert payment.status == PaymentStatus.CAPTURED
        assert payment.razorpay_payment_id == payment_id
