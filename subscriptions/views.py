import json
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsTenantAdmin, IsSuperAdmin
from .services import create_order, verify_razorpay_signature, process_webhook_event, activate_subscription_atomic
from .models import Subscription, SubscriptionStatus, Payment, WebhookEvent
from .serializers import SubscriptionSerializer, PaymentSerializer, WebhookEventSerializer
from .tasks import process_webhook_async
import traceback
from django.shortcuts import redirect
from django.urls import reverse
from core.authentication import CustomJWTAuthentication, SubscriptionTokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.apps import apps

# --- API VIEWS ---

class CreateOrderAPIView(APIView):
    """
    Endpoint for creating a Razorpay order.
    """
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request):
        try:
            subscription = create_order(request.user.organization)
            print(f"DEBUG: Created Razorpay Order {subscription.razorpay_order_id} for Org {request.user.organization.id}")
            return Response({
                "status": "success",
                "message": "Payment order created successfully",
                "data": {
                    "order_id": subscription.razorpay_order_id,
                    "amount": settings.PREMIUM_PLAN_AMOUNT, # use integer paise directly
                    "currency": subscription.currency,
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                    "organization_name": request.user.organization.name
                }
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({
                "status": "failed",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()  # Print the full error to the terminal
            return Response({
                "status": "error",
                "message": f"Failed to create payment order: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubscriptionStatusAPIView(APIView):
    """
    Endpoint for polling subscription status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            subscription = Subscription.objects.get(
                razorpay_order_id=order_id,
                organization=request.user.organization
            )
            return Response({
                "status": "success",
                "data": {
                    "subscription_status": subscription.status,
                    "is_premium": request.user.organization.is_premium
                }
            })
        except Subscription.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Subscription not found"
            }, status=status.HTTP_404_NOT_FOUND)


# --- ADMIN AUDIT VIEWSETS ---

class SubscriptionAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SuperAdmin view for all subscriptions.
    """
    queryset = Subscription.objects.all().order_by('-created_at')
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

class PaymentAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SuperAdmin view for all payments.
    """
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

class WebhookEventAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SuperAdmin view for all webhooks.
    """
    queryset = WebhookEvent.objects.all().order_by('-created_at')
    serializer_class = WebhookEventSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    """
    Endpoint for receiving Razorpay webhooks.
    """
    def post(self, request):
        print(f"\nDEBUG: [WEBHOOK] --- New Request Received at {timezone.now()} ---")
        print(f"DEBUG: [WEBHOOK] Headers: {dict(request.headers)}")
        
        signature = request.headers.get('X-Razorpay-Signature')
        if not signature:
            print("DEBUG: [WEBHOOK] Error: No signature found in headers")
            return HttpResponse(status=400)

        raw_payload = request.body
        try:
            payload = json.loads(raw_payload)
            event_type = payload.get('event')
            event_id = request.headers.get('X-Razorpay-Event-Id') # Reliable source from header
            
            print(f"DEBUG: [WEBHOOK] Processing Event: {event_type} | ID: {event_id}")
            
            is_new = process_webhook_event(raw_payload, signature, event_id=event_id)
            if is_new:
                process_webhook_async.delay(event_id)
            else:
                print(f"DEBUG: [WEBHOOK] Skipping Task Trigger - Event {event_id} already exists")
            
            return HttpResponse(status=200)
        except Exception as e:
            print(f"DEBUG: [WEBHOOK] Exception during processing: {str(e)}")
            traceback.print_exc()
            return HttpResponse(status=200)


# --- TEMPLATE VIEWS ---

@method_decorator(xframe_options_exempt, name='dispatch')
class UpgradePageView(APIView):
    """
    Renders the premium upgrade page with Razorpay integration.
    """
    authentication_classes = [SubscriptionTokenAuthentication, CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        # 2. Refresh Org Status
        org = request.user.organization
        org.refresh_from_db()
        
        if org.is_premium:
            return render(request, "subscriptions/already_premium.html")

        response = render(request, "subscriptions/upgrade.html", {
            "amount": int(settings.PREMIUM_PLAN_AMOUNT / 100),
            "currency": settings.PREMIUM_PLAN_CURRENCY,
            "key_id": settings.RAZORPAY_KEY_ID
        })
        
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class PaymentCallbackView(APIView):
    """
    Receives the response from Razorpay after payment attempt.
    """
    authentication_classes = [SubscriptionTokenAuthentication, CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request):
        token = request.GET.get('token') or request.POST.get('token')

        # 2. Extract Data
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id', 'unknown')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        # 3. Verify
        is_valid = verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
        

        if is_valid:
            try:
                subscription = Subscription.objects.get(razorpay_order_id=razorpay_order_id)
                activate_subscription_atomic(subscription, razorpay_payment_id, razorpay_signature)
                
                # Redirect to Success GET page (PRG Pattern)
                print(f"DEBUG: [CALLBACK] Verification Success. Redirecting to Success Page...")
                success_url = reverse('payment-success') + f"?payment_id={razorpay_payment_id}"
                if token:
                    success_url += f"&token={token}"
                return redirect(success_url)
            except Exception as e:
                print(f"DEBUG: [CALLBACK] Processing Error: {str(e)}")
                fail_url = reverse('payment-failure') + f"?error=Processing+failed"
                if token:
                    fail_url += f"&token={token}"
                return redirect(fail_url)
        else:
            print("DEBUG: [CALLBACK] Invalid Signature. Redirecting to Failure Page.")
            fail_url = reverse('payment-failure') + f"?error=Invalid+signature"
            if token:
                fail_url += f"&token={token}"
            return redirect(fail_url)

@method_decorator(xframe_options_exempt, name='dispatch')
class PaymentSuccessView(APIView):
    authentication_classes = [SubscriptionTokenAuthentication, CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        return render(request, "subscriptions/payment_success.html", {
            "payment_id": request.GET.get('payment_id', 'N/A')
        })

@method_decorator(xframe_options_exempt, name='dispatch')
class PaymentFailureView(APIView):
    authentication_classes = [SubscriptionTokenAuthentication, CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        return render(request, "subscriptions/payment_failure.html", {
            "error": request.GET.get('error', 'Unknown error')
        })
