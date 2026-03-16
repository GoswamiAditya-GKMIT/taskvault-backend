import pytest
from rest_framework import status
from django.urls import reverse
from tests.factories import TenantAdminFactory, SuperAdminFactory, NormalUserFactory

@pytest.mark.django_db
class TestSubscriptionAPI:
    """
    Test suite for subscription ordering and plan-based restrictions.
    """

    def test_create_order_tenant_admin_success(self, tenantadmin_client, mock_razorpay_client):
        """
        Verify that a Tenant Admin can initiate a subscription order.
        """
        fake_order_id = "order_fake123"
        mock_razorpay_client.return_value.order.create.return_value = {
            'id': fake_order_id,
            'amount': 100000,
            'currency': 'INR',
            'status': 'created'
        }
        
        url = reverse('subscription-orders')
        response = tenantadmin_client.post(url)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["order_id"] == fake_order_id
        mock_razorpay_client.return_value.order.create.assert_called_once()

    def test_create_order_normal_user_forbidden(self, user_client):
        """
        Verify that a normal user is forbidden from creating subscription orders.
        """
        url = reverse('subscription-orders')
        response = user_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_order_inactive_org_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that Tenant Admin with inactive organization cannot create orders.
        """
        org = tenantadmin_user.organization
        org.is_active = False
        org.save()
        url = reverse('subscription-orders')
        response = tenantadmin_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestSubscriptionAdminAPI:
    """
    Test suite for organization-wide subscription administration.
    """

    def test_list_all_subscriptions_super_admin_success(self, superadmin_client):
        """
        Verify that a Super Admin can access the subscription administrative dashboard.
        """
        url = reverse('admin-subscriptions-list')
        response = superadmin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

    def test_list_all_subscriptions_tenant_admin_forbidden(self, tenantadmin_client):
        """
        Verify that a Tenant Admin cannot access the global subscription dashboard.
        """
        url = reverse('admin-subscriptions-list')
        response = tenantadmin_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestWebhookAPI:
    """
    Test suite for Razorpay Webhook interactions.
    """

    def test_webhook_invalid_signature(self, api_client):
        """
        Verify that a webhook request with an invalid signature is rejected.
        """
        url = reverse('razorpay-webhook')
        payload = {"event": "payment.captured"}
        # Send without proper headers
        response = api_client.post(url, payload, format='json')
        assert response.status_code == 400

@pytest.mark.django_db
class TestSubscriptionPollingAPI:
    """
    Test suite for subscription status polling.
    """

    def test_polling_not_found(self, tenantadmin_client):
        """
        Verify that polling for a non-existent order returns 404.
        """
        url = reverse('subscription-status', kwargs={'order_id': 'non-existent'})
        response = tenantadmin_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
