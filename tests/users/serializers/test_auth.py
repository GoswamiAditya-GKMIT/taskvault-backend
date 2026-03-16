import pytest
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from django.contrib.auth import get_user_model
from users.serializers.auth import RegisterSerializer, LoginSerializer
from tests.factories import OrganizationFactory
from tests.factories import NormalUserFactory
from django.core.cache import cache
from unittest.mock import MagicMock

User = get_user_model()

@pytest.mark.django_db
class TestRegisterSerializer:
    """
    Unit tests for RegisterSerializer validation logic.
    """

    def test_register_serializer_valid_data(self, mocker):
        """
        Verify that a valid user registration payload is successful and correctly filters by organization.
        """
        org = OrganizationFactory(is_active=True)
        request = MagicMock()
        request.parser_context = {"kwargs": {"tenant_id": str(org.id)}}
        
        data = {
            "email": "newuser@example.com",
            "username": "validuser",
            "first_name": "John",
            "last_name": "Doe",
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123"
        }
        
        serializer = RegisterSerializer(data=data, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["organization"] == org

    def test_register_serializer_passwords_mismatch(self, mocker):
        """
        Verify that user registration fails when the password and confirm_password do not match.
        """
        org = OrganizationFactory(is_active=True)
        request = MagicMock()
        request.parser_context = {"kwargs": {"tenant_id": str(org.id)}}
        
        data = {
            "email": "newuser@example.com",
            "username": "validuser",
            "first_name": "John",
            "last_name": "Doe",
            "password": "StrongPassword@123",
            "confirm_password": "WrongPassword@123"
        }
        
        serializer = RegisterSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "confirm_password" in serializer.errors
        assert serializer.errors["confirm_password"][0] == "Passwords do not match."

    def test_register_serializer_username_too_short(self):
        """
        Verify that a username shorter than the minimum required length is rejected.
        """
        data = {"username": "abc"}
        data = {"username": "abc"}
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert "username" in serializer.errors

    def test_register_serializer_username_numeric_only(self):
        """
        Verify that a username consisting only of numeric characters is rejected.
        """
        serializer = RegisterSerializer()
        serializer = RegisterSerializer()
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_username("1234567")
        assert "Username cannot consist of only numbers." in str(exc.value)

    def test_register_serializer_names_alpha_check(self):
        """
        Verify that first and last names are validated to contain only alphabetic characters.
        """
        serializer = RegisterSerializer()
        serializer = RegisterSerializer()
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_first_name("John123")
        assert "it should only contain alphabets" in str(exc.value)

    def test_register_serializer_inactive_org(self, mocker):
        """
        Verify that registration fails if the target organization is inactive.
        """
        org = OrganizationFactory(is_active=False)
        org = OrganizationFactory(is_active=False)
        request = MagicMock()
        request.parser_context = {"kwargs": {"tenant_id": str(org.id)}}
        
        data = {
            "email": "newuser@example.com",
            "username": "validuser",
            "first_name": "John",
            "last_name": "Doe",
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123"
        }
        
        serializer = RegisterSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "organization" in serializer.errors

@pytest.mark.django_db
class TestLoginSerializer:
    """
    Unit tests for LoginSerializer validation logic.
    """

    def test_login_serializer_success(self, mocker):
        """
        Verify that a user can successfully log in with valid credentials.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True, password="StrongPassword@123")
        mocker.patch('users.serializers.auth.send_user_verification_otp.delay')
        
        data = {
            "username": user.username,
            "password": "StrongPassword@123"
        }
        
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["user"] == user

    def test_login_serializer_unverified_email(self):
        """
        Verify that login is forbidden for users who have not yet verified their email.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=False, password="StrongPassword@123")
        data = {
            "username": user.username,
            "password": "StrongPassword@123"
        }
        serializer = LoginSerializer(data=data)
        with pytest.raises(PermissionDenied) as exc:
            serializer.is_valid(raise_exception=True)
        assert "Email verification pending." in str(exc.value)

    def test_login_serializer_inactive_user(self):
        """
        Verify that login is forbidden for deactivated user accounts.
        """
        user = NormalUserFactory(is_active=False, is_email_verified=True, password="StrongPassword@123")
        data = {
            "username": user.username,
            "password": "StrongPassword@123"
        }
        serializer = LoginSerializer(data=data)
        with pytest.raises(PermissionDenied) as exc:
            serializer.is_valid(raise_exception=True)
        assert "User account inactive." in str(exc.value)

    def test_login_serializer_rate_limit(self, mocker):
        """
        Verify that login rate limiting (cooldown) prevents excessive OTP requests.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True, password="StrongPassword@123")
        cooldown_key = f"login_otp_cooldown:{user.id}"
        cache.set(cooldown_key, True, timeout=60)
        
        data = {
            "username": user.username,
            "password": "StrongPassword@123"
        }
        serializer = LoginSerializer(data=data)
        from rest_framework.exceptions import AuthenticationFailed
        with pytest.raises(AuthenticationFailed) as exc:
            serializer.is_valid(raise_exception=True)
        assert "OTP already sent" in str(exc.value)
