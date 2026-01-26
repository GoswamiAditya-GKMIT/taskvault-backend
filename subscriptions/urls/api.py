from django.urls import path, include
from rest_framework.routers import DefaultRouter
from subscriptions.views import (
    CreateOrderAPIView, RazorpayWebhookView, SubscriptionStatusAPIView,
    SubscriptionAdminViewSet, PaymentAdminViewSet, WebhookEventAdminViewSet
)

# Admin Router
admin_router = DefaultRouter()
admin_router.register(r'subscriptions', SubscriptionAdminViewSet, basename='admin-subscriptions')
admin_router.register(r'payments', PaymentAdminViewSet, basename='admin-payments')
admin_router.register(r'webhooks', WebhookEventAdminViewSet, basename='admin-webhooks')

urlpatterns = [    
    # API endpoints (Accessible via /api/v1/subscriptions/...)
    path('orders/', CreateOrderAPIView.as_view(), name='subscription-orders'),
    path('status/<str:order_id>/', SubscriptionStatusAPIView.as_view(), name='subscription-status'),
    path('webhooks/razorpay/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    
    # Admin Audit Endpoints
    path('', include(admin_router.urls)),
]
