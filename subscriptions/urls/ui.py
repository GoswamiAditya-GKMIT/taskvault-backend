from django.urls import path
from subscriptions.views import UpgradePageView, PaymentCallbackView, PaymentSuccessView, PaymentFailureView

urlpatterns = [
    # UI endpoints (Accessible via /subscriptions/...)
    path('upgrade/', UpgradePageView.as_view(), name='upgrade-page'),
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('success/', PaymentSuccessView.as_view(), name='payment-success'),
    path('failure/', PaymentFailureView.as_view(), name='payment-failure'),
]
