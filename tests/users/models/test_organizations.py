import pytest
from users.models import Organization
from tests.factories import OrganizationFactory

@pytest.mark.django_db
class TestOrganizationModel:
    """
    Test suite for Organization model basic functionality.
    """

    def test_organization_creation_success(self):
        """
        Verify that an organization can be created and has expected string representation.
        """
        org = OrganizationFactory(name="Test Org")
        assert org.name == "Test Org"
        assert str(org) == "Test Org"

    def test_organization_name_whitespace_stripping(self):
        """
        Verify that organization name is stripped of multiple internal and outer whitespaces on save.
        """
        org = Organization.objects.create(name="  Test    Org   ")
        assert org.name == "Test Org"

    def test_organization_default_states(self):
        """
        Verify that a new organization is active and NOT premium by default.
        """
        org = Organization.objects.create(name="Default Org")
        assert org.is_active is True
        assert org.is_premium is False
