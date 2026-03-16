import pytest
from django.contrib.auth import get_user_model
from tests.factories import UserFactory, OrganizationFactory
from core.choices import UserRoleChoices

User = get_user_model()

@pytest.mark.django_db
class TestUserModel:
    """
    Test suite for User model basic functionality and defaults.
    """

    def test_user_creation_success(self):
        """
        Verify that a user can be created with required fields.
        """
        user = UserFactory(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert str(user) == f"{user.email} ({user.role})"

    def test_user_default_role(self):
        """
        Verify that a new user has the default 'USER' role.
        """
        user = User.objects.create_user(username="defaultrole", email="default@example.com", password="pass")
        assert user.role == UserRoleChoices.USER

    def test_user_email_verified_default(self):
        """
        Verify that a new user has is_email_verified=False by default.
        """
        user = User.objects.create_user(username="unverified", email="unverified@example.com", password="pass")
        assert user.is_email_verified is False
