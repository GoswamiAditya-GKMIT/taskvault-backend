import logging
import json
from celery import shared_task
from django.utils import timezone
from .models import WebhookEvent, Subscription, SubscriptionStatus
from .services import activate_subscription_atomic, reconcile_pending_orders

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_webhook_async(self, event_id):

    try:
        event = WebhookEvent.objects.get(event_id=event_id)
        if event.is_processed:
            logger.info(f"Task Skipped: Event {event_id} already processed")
            return "Already processed"

        payload = event.payload
        event_type = event.event_type
        
        # 1. Handle Payment Captured
        if event_type == "payment.captured":
            razorpay_order_id = payload['payload']['payment']['entity']['order_id']
            razorpay_payment_id = payload['payload']['payment']['entity']['id']
            
            try:
                subscription = Subscription.objects.get(razorpay_order_id=razorpay_order_id)
                activate_subscription_atomic(subscription, razorpay_payment_id)
            except Subscription.DoesNotExist:
                # This could happen if webhook is faster than DB commit of create_order
                # or if it's an unrelated payment
                pass

        # 2. Handle Order Paid (Backup to payment.captured)
        elif event_type == "order.paid":
            razorpay_order_id = payload['payload']['order']['entity']['id']
            # Find associated payment
            payments = payload['payload'].get('payment', {})
            if payments:
                razorpay_payment_id = payments['entity']['id']
                try:
                    subscription = Subscription.objects.get(razorpay_order_id=razorpay_order_id)
                    activate_subscription_atomic(subscription, razorpay_payment_id)
                except Subscription.DoesNotExist:
                    pass

        # 3. Handle Payment Failed
        elif event_type == "payment.failed":
             razorpay_order_id = payload['payload']['payment']['entity']['order_id']
             # Update Subscription
             Subscription.objects.filter(razorpay_order_id=razorpay_order_id).update(status=SubscriptionStatus.FAILED)
             
             # Reverse Premium Status if it was activated (Safety against race conditions)
             try:
                 subscription = Subscription.objects.get(razorpay_order_id=razorpay_order_id)
                 org = subscription.organization
                 org.is_premium = False
                 org.save(update_fields=['is_premium'])
             except Subscription.DoesNotExist:
                 pass

        # Mark as processed
        event.is_processed = True
        event.processed_at = timezone.now()
        event.save()
        logger.info(f"Task Completed: Processed {event_type} for Event ID {event_id}")
        return f"Processed {event_type}"

    except Exception as e:
        logger.error(f"Task Failed: process_webhook_async failed for {event_id}: {str(e)}", exc_info=True)
        if 'event' in locals():
            event.processing_error = str(e)
            event.save()
        raise e


@shared_task(name="subscriptions.tasks.reconcile_pending_subscriptions_job")
def reconcile_pending_subscriptions_job():
    """
    Periodic task to reconcile pending subscriptions by polling Razorpay API.
    """
    reconcile_pending_orders()
    return "Reconciliation complete"
