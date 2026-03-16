import pytest
from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.serializers.user import UserCreateSerializer, UserUpdateSerializer, InviteUserSerializer
from tests.factories import OrganizationFactory
from tests.factories import SuperAdminFactory, TenantAdminFactory, NormalUserFactory
from django.core.cache import cache
from unittest.mock import MagicMock
from core.choices import UserRoleChoices

User = get_user_model()

@pytest.mark.django_db
class TestUserCreateSerializer:
    """
    Unit tests for UserCreateSerializer validation logic.
    """

    def test_user_create_serializer_tenant_admin_success(self, mocker):
        """
        Verify that a Tenant Admin can create a new user within their organization with valid data.
        """
        admin = TenantAdminFactory()
        request = MagicMock()
        request.user = admin
        
        data = {
            "email": "newuser@example.com",
            "username": "newvaliduser",
            "first_name": "Jane",
            "last_name": "Doe",
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123"
        }
        
        serializer = UserCreateSerializer(data=data, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        # Verify role assignment
        validated_data = serializer.validated_data
        # Note: role is assigned in create() usually, but let's check validation logic
        # Actually in UserCreateSerializer.create, it sets the role.

    def test_user_create_serializer_super_admin_requires_org(self, mocker):
        """
        Verify that a Super Admin must specify an organization ID when creating a Tenant Admin.
        """
        super_admin = SuperAdminFactory()
        request = MagicMock()
        request.user = super_admin
        
        data = {
            "email": "tenant@example.com",
            "username": "tenantadmin",
            "first_name": "Jane",
            "last_name": "Doe",
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123"
            # Missing organization_id
        }
        
        serializer = UserCreateSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "organization_id" in serializer.errors

    def test_user_create_serializer_username_numeric(self):
        """
        Verify that creating a user with a purely numeric username is rejected.
        """
        serializer = UserCreateSerializer()
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_username("1234567")
        assert "Username cannot consist of only numbers." in str(exc.value)

@pytest.mark.django_db
class TestUserUpdateSerializer:
    """
    Unit tests for UserUpdateSerializer validation logic.
    """

    def test_user_update_serializer_alpha_names(self):
        """
        Verify that user names must contain only alphabetic characters during an update.
        """
        user = NormalUserFactory()
        serializer = UserUpdateSerializer(instance=user)
        
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_first_name("John1")
        assert "First name must contain only alphabets." in str(exc.value)

    def test_user_update_serializer_no_changes(self):
        """
        Verify that updating a user with no changed values is rejected to prevent redundant saves.
        """
        user = NormalUserFactory(first_name="Original")
        data = {"first_name": "Original"}
        serializer = UserUpdateSerializer(instance=user, data=data)
        assert not serializer.is_valid()
        assert "No changes detected" in str(serializer.errors["non_field_errors"][0])

    def test_user_update_serializer_is_active_restriction(self):
        """
        Verify that a normal user cannot change their own 'is_active' status.
        """
        user = NormalUserFactory(is_active=True)
        # Normal user trying to change their own is_active
        data = {"is_active": False}
        serializer = UserUpdateSerializer(instance=user, data=data, context={"request_user": user})
        assert not serializer.is_valid()
        assert "is_active" in serializer.errors

@pytest.mark.django_db
class TestInviteUserSerializer:
    """
    Unit tests for InviteUserSerializer validation logic.
    """

    def test_invite_user_serializer_only_tenant_admin(self):
        """
        Verify that only users with the Tenant Admin role can send user invitations.
        """
        normal_user = NormalUserFactory()
        request = MagicMock()
        request.user = normal_user
        
        data = {"email": "invitee@example.com"}
        serializer = InviteUserSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "Only tenant admins can invite users." in str(serializer.errors["non_field_errors"][0])

    def test_invite_user_serializer_success(self):
        """
        Verify that a Tenant Admin can successfully provide an email for user invitation.
        """
        admin = TenantAdminFactory()
        request = MagicMock()
        request.user = admin
        
        data = {"email": "invitee@example.com"}
        serializer = InviteUserSerializer(data=data, context={"request": request})
        assert serializer.is_valid(), serializer.errors
