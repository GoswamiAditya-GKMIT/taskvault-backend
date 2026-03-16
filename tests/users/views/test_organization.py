import pytest
from rest_framework import status
from django.urls import reverse
from users.models import Organization
from tests.factories import OrganizationFactory

@pytest.mark.django_db
class TestOrganizationAPI:
    """
    Test suite for organization management (CRUD) by Super Admins.
    """

    def test_list_organizations_super_admin_success(self, superadmin_client):
        """
        Verify that a Super Admin can list all organizations.
        """
        OrganizationFactory.create_batch(3)
        url = reverse('organization-list-create')
        
        response = superadmin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) >= 3

    def test_list_organizations_tenant_admin_forbidden(self, tenantadmin_client):
        """
        Verify that a Tenant Admin is forbidden from listing organizations.
        """
        url = reverse('organization-list-create')
        response = tenantadmin_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_organization_super_admin_success(self, superadmin_client):
        """
        Verify that a Super Admin can create a new organization.
        """
        url = reverse('organization-list-create')
        payload = {"name": "Super Admin Created Org", "is_premium": True}
        
        response = superadmin_client.post(url, payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Organization.objects.filter(name="Super Admin Created Org").exists()

    def test_create_organization_tenant_admin_forbidden(self, tenantadmin_client):
        """
        Verify that a Tenant Admin is forbidden from creating an organization.
        """
        url = reverse('organization-list-create')
        payload = {"name": "Illegal Org"}
        
        response = tenantadmin_client.post(url, payload)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_organization_super_admin_success(self, superadmin_client):
        """
        Verify that a Super Admin can update an organization's details.
        """
        org = OrganizationFactory(name="Old Name")
        url = reverse('organization-detail-update-delete', kwargs={'id': org.id})
        payload = {"name": "New Name"}
        
        response = superadmin_client.patch(url, payload)
        
        assert response.status_code == status.HTTP_200_OK
        org.refresh_from_db()
        assert org.name == "New Name"

    def test_deactivate_organization_success(self, superadmin_client):
        """
        Verify that a Super Admin can deactivate (soft-delete) an organization.
        """
        org = OrganizationFactory(is_active=True)
        url = reverse('organization-detail-update-delete', kwargs={'id': org.id})
        
        response = superadmin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        org.refresh_from_db()
        assert org.is_active is False
