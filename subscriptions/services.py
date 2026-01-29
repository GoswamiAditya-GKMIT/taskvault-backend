import json
import decimal
import uuid
import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Subscription, Payment, WebhookEvent, SubscriptionStatus, PaymentStatus, PlanType
from users.models import Organization
from core.constants import RECONCILE_TIME , RECONSILE_FAILED_ORDER_TTL

# Initialize Razorpay Client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_order(organization: Organization) -> Subscription:
    """
    Creates a Razorpay order and a pending subscription record.
    """
    # 1. Validate: Check if organization already has an active subscription
    print(f"DEBUG: Checking order for Org {organization.id} | Is Premium: {organization.is_premium}")
    if Subscription.objects.filter(organization=organization, status=SubscriptionStatus.ACTIVE).exists():
        raise ValueError("Organization already has an active premium subscription.")

    # 2. Razorpay Order Creation
    amount_paise = settings.PREMIUM_PLAN_AMOUNT
    order_data = {
        "amount": amount_paise,
        "currency": settings.PREMIUM_PLAN_CURRENCY,
        "payment_capture": 1,  # Auto-capture payment
        "notes": {
            "organization_id": str(organization.id),
            "plan_type": PlanType.LIFETIME
        }
    }
    
    try:
        razorpay_order = client.order.create(data=order_data)
    except Exception as e:
        # Log error in real implementation
        raise RuntimeError(f"Error creating Razorpay order: {str(e)}")

    # 3. Save to DB atomically
    with transaction.atomic():
        subscription, created = Subscription.objects.update_or_create(
            organization=organization,
            defaults={
                "plan_type": PlanType.LIFETIME,
                "status": SubscriptionStatus.PENDING_PAYMENT,
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_payment_id": None,
                "razorpay_signature": None,
                "amount": decimal.Decimal(settings.PREMIUM_PLAN_AMOUNT) / 100,
                "currency": settings.PREMIUM_PLAN_CURRENCY,
                "updated_at": timezone.now()
            }
        )
        
        Payment.objects.create(
            subscription=subscription,
            razorpay_order_id=razorpay_order['id'],
            amount=subscription.amount,
            currency=subscription.currency,
            status=PaymentStatus.CREATED
        )
        
    return subscription

def verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature) -> bool:
    """
    Verifies the payment signature provided by the frontend/callback.
    """
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False

@transaction.atomic
def activate_subscription_atomic(subscription: Subscription, razorpay_payment_id: str, razorpay_signature: str = None) -> None:
    """
    Atomically activates a subscription and updates the organization.
    """
    # 1. Refresh from DB and lock the row
    subscription = Subscription.objects.select_for_update().get(id=subscription.id)
    
    # 2. Check if already active
    if subscription.status == SubscriptionStatus.ACTIVE:
        print(f"DEBUG: Activation skipped for {subscription.razorpay_order_id} (Already Active)")
        return

    print(f"DEBUG: STARTING ACTIVATION for Order {subscription.razorpay_order_id} | Payment ID: {razorpay_payment_id}")
    # 3. Update Subscription
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.razorpay_payment_id = razorpay_payment_id
    if razorpay_signature:
        subscription.razorpay_signature = razorpay_signature
    subscription.activated_at = timezone.now()
    subscription.save()

    # 4. Update Organization
    org = subscription.organization
    org.is_premium = True
    org.save(update_fields=['is_premium'])
    print(f"DEBUG: Organization {org.id} is now PREMIUM")

    # 5. Update Payment Record
    payment = Payment.objects.filter(
        subscription=subscription, 
        razorpay_order_id=subscription.razorpay_order_id
    ).first()
    
    if payment:
        payment.status = PaymentStatus.CAPTURED
        payment.razorpay_payment_id = razorpay_payment_id
        payment.save()

def process_webhook_event(raw_payload: bytes, signature: str, event_id: str = None) -> None:
    """
    Validates and stores a webhook event, then dispatches for processing.
    """
    # 1. Signature Verification
    try:
        client.utility.verify_webhook_signature(raw_payload.decode('utf-8'), signature, settings.RAZORPAY_WEBHOOK_SECRET)
    except razorpay.errors.SignatureVerificationError:
        # In production, log this as a security concern
        raise ValueError("Invalid webhook signature.")

    payload = json.loads(raw_payload)
    
    # Use provided event_id or fallback to payload
    if not event_id:
        event_id = payload.get('id') or f"evt_{uuid.uuid4().hex[:12]}"

    # 2. Check for duplicate event (Idempotency)
    if WebhookEvent.objects.filter(event_id=event_id).exists():
        return False

    # 3. Save event to DB
    WebhookEvent.objects.create(
        event_id=event_id,
        event_type=payload.get('event'),
        payload=payload,
        signature=signature,
        is_verified=True
    )
    return True
    
    # 4. Success - Task will be triggered from view to process it async

def reconcile_pending_orders():
    """
    Polling fallback to check status of pending subscriptions.
    Checks orders older than 5 minutes.
    """
    # Fetch orders pending for more than 5 minutes
    threshold = timezone.now() - timezone.timedelta(minutes=RECONCILE_TIME)
    pending_subs = Subscription.objects.filter(
        status=SubscriptionStatus.PENDING_PAYMENT,
        created_at__lt=threshold
    )

    for sub in pending_subs:
        try:
            order = client.order.fetch(sub.razorpay_order_id)
            if order.get('status') == 'paid':
                # Order is paid, find a successful payment associated with it
                payments = client.order.payments(sub.razorpay_order_id)
                if payments and payments.get('items'):
                    # Find any captured or authorized payment in the list
                    razorpay_payment = next((p for p in payments['items'] if p['status'] in ['captured', 'authorized']), None)
                    if razorpay_payment:
                        activate_subscription_atomic(sub, razorpay_payment['id'])
            elif order.get('status') == 'attempted' and sub.created_at < timezone.now() - timezone.timedelta(hours=RECONSILE_FAILED_ORDER_TTL):
                # Mark as failed if no success after 24 hours
                sub.status = SubscriptionStatus.FAILED
                sub.save()
        except Exception as e:
            # Continue to next if one fails
            print(f"Error reconciling order {sub.razorpay_order_id}: {str(e)}")
            
#     Handles payment failure callbacks.Marks Subscription and Payment as FAILED.

@transaction.atomic
def handle_payment_failure(razorpay_order_id: str, razorpay_payment_id: str = None, error_description: str = "Payment Failed"):
    try:
        subscription = Subscription.objects.select_for_update().get(razorpay_order_id=razorpay_order_id)
        
        # If payment_id is missing, try to fetch it from Razorpay
        if not razorpay_payment_id:
             try:
                 payments = client.order.payments(razorpay_order_id)
                 if payments and payments.get('items'):
                     # Get the most recent payment attempt
                     latest_payment = payments['items'][0] # Items are usually returned sorted desc by created_at, but verify logic if needed
                     razorpay_payment_id = latest_payment.get('id')
                     print(f"DEBUG: Fetched missing Payment ID {razorpay_payment_id} from Razorpay API")
             except Exception as e:
                 print(f"DEBUG: Failed to fetch payments from Razorpay: {e}")

        # Update Subscription
        if subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.FAILED
            subscription.razorpay_payment_id = razorpay_payment_id
            subscription.save()

        # Create or Update Payment Record
        # Search for existing payment record
        payment = Payment.objects.filter(
            subscription=subscription,
            razorpay_order_id=razorpay_order_id
        ).first()

        if payment:
            payment.status = PaymentStatus.FAILED
            payment.razorpay_payment_id = razorpay_payment_id
            payment.error_message = error_description
            payment.save()
        else:
             # Create a new failed payment record
            Payment.objects.create(
                subscription=subscription,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                amount=subscription.amount,
                currency=subscription.currency,
                status=PaymentStatus.FAILED,
                error_message=error_description
            )

    except Subscription.DoesNotExist:
        print(f"DEBUG: Subscription not found for order {razorpay_order_id}")
    except Exception as e:
        print(f"DEBUG: Error handling payment failure: {str(e)}")
