import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tests.factories import (
    SuperAdminFactory, TenantAdminFactory, NormalUserFactory, OrganizationFactory
)

@pytest.fixture
def api_client():
    """Returns an unauthenticated APIClient."""
    return APIClient()

@pytest.fixture
def get_auth_client():
    """
    Given a user object, generates a JWT token for them and returns an
    APIClient configured with the Bearer token in the headers.
    """
    def _get_auth_client(user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client
    return _get_auth_client

@pytest.fixture
def superadmin_user(db):
    return SuperAdminFactory()

@pytest.fixture
def superadmin_client(get_auth_client, superadmin_user):
    return get_auth_client(superadmin_user)

@pytest.fixture
def tenantadmin_user(db):
    return TenantAdminFactory()

@pytest.fixture
def tenantadmin_client(get_auth_client, tenantadmin_user):
    return get_auth_client(tenantadmin_user)

@pytest.fixture
def normal_user(db):
    return NormalUserFactory()

@pytest.fixture
def user_client(get_auth_client, normal_user):
    return get_auth_client(normal_user)

@pytest.fixture
def active_organization(db):
    return OrganizationFactory(is_active=True, is_premium=False)

@pytest.fixture
def premium_organization(db):
    return OrganizationFactory(is_active=True, is_premium=True)

@pytest.fixture
def inactive_organization(db):
    return OrganizationFactory(is_active=False, is_premium=False)
