import pytest
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from tests.factories import TenantAdminFactory, NormalUserFactory, SuperAdminFactory, UserFactory
pkgs = ["tests.factories.user", "tests.factories.organization"] # Unused for reference
from tests.factories import OrganizationFactory
from tests.factories import UserPayloadFactory
from core.permissions import (
    IsSuperAdmin, IsTenantAdmin, IsTenantAdminOrSuperAdmin,
    CanViewTask, CanCreateTask, CanUpdateTask, CanDeleteTask,
    CanViewOrCreateComment, CanUpdateComment, CanDeleteComment,
    CanViewTaskHistory, CanAccessUser, CanRestoreUser, CanDeleteUser
)
from core.choices import UserRoleChoices
from unittest.mock import MagicMock

User = get_user_model()

@pytest.mark.django_db
class TestUserListAPI:
    """
    Test suite for user listing behavior across different roles and organizations.
    """

    def test_list_users_unauthenticated_forbidden(self, api_client):
        """
        Verify that unauthenticated access is forbidden.
        """
        url = reverse('user-list-create')
        assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_users_inactive_org_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that users in an inactive organization are forbidden from listing users.
        """
        tenantadmin_user.organization.is_active = False
        tenantadmin_user.organization.save()
        url = reverse('user-list-create')
        assert tenantadmin_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_normal_user_is_tenant_admin_or_super_admin_fallthrough(self, user_client):
        """
        Verify that a normal user fails the IsTenantAdminOrSuperAdmin permission check.
        """
        url = reverse('user-list-create')
        assert user_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_tenant_admin_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can see all users within their organization excluding themselves.
        """
        org = tenantadmin_user.organization
        same_org_user = NormalUserFactory(organization=org)
        other_org_user = NormalUserFactory() # Different org
        
        url = reverse('user-list-create')
        response = tenantadmin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["data"]]
        assert same_org_user.email in emails
        assert tenantadmin_user.email not in emails # View filters out self
        assert other_org_user.email not in emails # Tenancy isolation

    def test_list_users_normal_user_forbidden(self, user_client):
        """
        Verify that a normal user is forbidden from listing users.
        """
        url = reverse('user-list-create')
        response = user_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_super_admin_success(self, superadmin_client):
        """
        Verify that a Super Admin can see all Tenant Admins.
        """
        tenant_admin = TenantAdminFactory()
        url = reverse('user-list-create')
        
        response = superadmin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["data"]]
        assert tenant_admin.email in emails

@pytest.mark.django_db
class TestUserCreateAPI:
    """
    Test suite for user creation and invitations.
    """

    def test_create_user_tenant_admin_success(self, tenantadmin_client, mocker):
        """
        Verify that a Tenant Admin can create a new user within their organization.
        """
        mock_send = mocker.patch('users.views.user.send_verification_link_email.delay')
        url = reverse('user-list-create')
        payload = UserPayloadFactory()
        
        response = tenantadmin_client.post(url, payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email=payload["email"]).exists()
        mock_send.assert_called_once()

    def test_create_user_duplicate_email(self, tenantadmin_client):
        """
        Verify that creating a user with an already registered email returns a validation error.
        """
        existing_user = NormalUserFactory()
        url = reverse('user-list-create')
        payload = UserPayloadFactory(email=existing_user.email)
        
        response = tenantadmin_client.post(url, payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "A user with this email already exists" in str(response.data["error"]["email"])

    def test_create_user_forbidden_normal_user(self, user_client):
        """
        Verify that a normal user cannot create other users.
        """
        url = reverse('user-list-create')
        payload = UserPayloadFactory()
        
        response = user_client.post(url, payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestUserUpdateDeleteAPI:
    """
    Test suite for updating, deleting, and restoring users.
    """

    def test_update_user_self_success(self, user_client, normal_user):
        """
        Verify that a user can update their own profile information.
        """
        url = reverse('user-detail-update-delete', kwargs={'id': normal_user.id})
        payload = {"first_name": "UpdatedName"}
        
        response = user_client.patch(url, payload)
        
        assert response.status_code == status.HTTP_200_OK
        normal_user.refresh_from_db()
        assert normal_user.first_name == "UpdatedName"

    def test_update_other_user_forbidden(self, user_client):
        """
        Verify that a normal user cannot update another user's profile.
        """
        other_user = NormalUserFactory()
        url = reverse('user-detail-update-delete', kwargs={'id': other_user.id})
        payload = {"first_name": "Hacker"}
        
        response = user_client.patch(url, payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_tenancy_leakage_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that Tenant Admin cannot update a user from a different organization.
        """
        other_user = UserFactory()  # Belongs to a different organization
        url = reverse('user-detail-update-delete', kwargs={'id': other_user.id})
        payload = {"first_name": "Hacker"}
        
        response = tenantadmin_client.patch(url, payload)
        # It's 403 because CanAccessUser denies it before other checks
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_detail_super_admin_access_restricted(self, superadmin_client, normal_user):
        """
        Verify that Super Admin can only access Tenant Admin profiles, not normal Users.
        """
        url = reverse('user-detail-update-delete', kwargs={'id': normal_user.id})
        response = superadmin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_restore_user_permission_edge_cases(self, tenantadmin_client, tenantadmin_user, superadmin_client):
        """
        Verify edge cases for user restoration (cross-org, active org check, role restrictions).
        """
        from users.models import User
        # 1. Tenant Admin trying to restore other organization user
        other_user = UserFactory(is_active=False)
        url = reverse('user-restore', kwargs={'id': other_user.id})
        assert tenantadmin_client.post(url).status_code == status.HTTP_403_FORBIDDEN

        # 2. Super Admin trying to restore a normal User
        assert superadmin_client.post(url).status_code == status.HTTP_403_FORBIDDEN

        # 3. Tenant Admin with inactive organization
        org = tenantadmin_user.organization
        org.is_active = False
        org.save()
        target = UserFactory(organization=org, is_active=False, role="USER")
        url = reverse('user-restore', kwargs={'id': target.id})
        assert tenantadmin_client.post(url).status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_permission_edge_cases(self, tenantadmin_client, tenantadmin_user, superadmin_client):
        """
        Verify edge cases for user deletion (self-deletion for admins, cross-org blocks).
        """
        # 1. Tenant Admin trying to delete themselves (Forbidden by logic)
        url = reverse('user-detail-update-delete', kwargs={'id': tenantadmin_user.id})
        assert tenantadmin_client.delete(url).status_code == status.HTTP_403_FORBIDDEN

        # 2. Super Admin trying to delete a normal user
        target = UserFactory(role="USER")
        url = reverse('user-detail-update-delete', kwargs={'id': target.id})
        assert superadmin_client.delete(url).status_code == status.HTTP_403_FORBIDDEN

        # 3. Super Admin trying to delete a Tenant Admin whose Org is inactive
        inactive_org_admin = TenantAdminFactory()
        inactive_org_admin.organization.is_active = False
        inactive_org_admin.organization.save()
        url = reverse('user-detail-update-delete', kwargs={'id': inactive_org_admin.id})
        assert superadmin_client.delete(url).status_code == status.HTTP_403_FORBIDDEN

        # 4. Tenant Admin trying to delete a user from another organization
        other_user = UserFactory(role="USER") 
        url = reverse('user-detail-update-delete', kwargs={'id': other_user.id})
        assert tenantadmin_client.delete(url).status_code == status.HTTP_403_FORBIDDEN

    def test_soft_delete_user_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can soft-delete a user in their organization.
        """
        user_to_delete = NormalUserFactory(organization=tenantadmin_user.organization)
        url = reverse('user-detail-update-delete', kwargs={'id': user_to_delete.id})
        
        response = tenantadmin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        user_to_delete.refresh_from_db()
        assert user_to_delete.deleted_at is not None

    def test_restore_user_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can restore a soft-deleted user in their organization.
        """
        user_to_restore = NormalUserFactory(organization=tenantadmin_user.organization)
        from users.services import soft_delete_user
        soft_delete_user(user_to_restore, tenantadmin_user)
        
        url = reverse('user-restore', kwargs={'id': user_to_restore.id})
        response = tenantadmin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        user_to_restore.refresh_from_db()
        assert user_to_restore.deleted_at is None

@pytest.mark.django_db
class TestPermissionLogicDirect:
    """
    Direct unit tests for permission classes to hit branches unreachable via API.
    """
    
    def test_cant_view_task_fallthrough(self):
        """
        Verify the fallthrough (False) return when a user has an invalid role for viewing tasks.
        """
        perm = CanViewTask()
        request = MagicMock()
        request.user.role = "NON_EXISTENT_ROLE"
        request.user.organization.is_active = True
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_is_tenant_admin_inactive_org(self):
        """
        Verify that IsTenantAdmin returns False if the organization is inactive.
        """
        perm = IsTenantAdmin()
        request = MagicMock()
        request.user.organization.is_active = False
        assert perm.has_permission(request, None) is False

    def test_is_tenant_admin_or_super_admin_unauthenticated(self):
        """
        Verify that IsTenantAdminOrSuperAdmin returns False for unauthenticated users.
        """
        perm = IsTenantAdminOrSuperAdmin()
        request = MagicMock()
        request.user.is_authenticated = False
        assert perm.has_permission(request, None) is False

    def test_can_update_task_user_success(self):
        """
        Verify that a normal user can update a task they own.
        """
        perm = CanUpdateTask()
        request = MagicMock()
        request.method = 'PUT'
        request.user.role = UserRoleChoices.USER
        obj = MagicMock()
        obj.owner = request.user
        assert perm.has_object_permission(request, None, obj) is True

    def test_can_delete_task_user_success(self):
        """
        Verify that a normal user can delete a task they own.
        """
        perm = CanDeleteTask()
        request = MagicMock()
        request.method = 'DELETE'
        request.user.role = UserRoleChoices.USER
        obj = MagicMock()
        obj.owner = request.user
        assert perm.has_object_permission(request, None, obj) is True

    def test_can_delete_user_self_deletion_and_super_admin_success(self, db):
        """
        Verify self-deletion for normal users and Super Admin's ability to delete Tenant Admins.
        """
        perm = CanDeleteUser()
        request = MagicMock()
        request.method = 'DELETE'
        
        # Self deletion for normal user
        user = UserFactory(role=UserRoleChoices.USER)
        request.user = user
        assert perm.has_object_permission(request, None, user) is True
        
        # Super Admin deleting Tenant Admin (Success)
        super_admin = UserFactory(role=UserRoleChoices.SUPER_ADMIN)
        tenant_admin = TenantAdminFactory()
        request.user = super_admin
        assert perm.has_object_permission(request, None, tenant_admin) is True
        
        # Tenant Admin cross-org block (Line 397)
        tenant_admin_actor = TenantAdminFactory()
        other_user = UserFactory(role=UserRoleChoices.USER)
        request.user = tenant_admin_actor
        assert perm.has_object_permission(request, None, other_user) is False

    def test_can_update_task_fallthrough(self):
        """
        Verify update task fallthrough for invalid user roles.
        """
        perm = CanUpdateTask()
        request = MagicMock()
        request.method = 'PUT'
        request.user.role = "INVALID"
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_can_delete_task_fallthrough(self):
        """
        Verify delete task fallthrough for invalid user roles.
        """
        perm = CanDeleteTask()
        request = MagicMock()
        request.method = 'DELETE'
        request.user.role = "INVALID"
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_can_view_or_create_comment_fallthrough(self):
        """
        Verify comment creation/view fallthrough for invalid user roles.
        """
        perm = CanViewOrCreateComment()
        request = MagicMock()
        request.user.role = "INVALID"
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_can_update_comment_fallthrough(self):
        """
        Verify comment update fallthrough for invalid user roles.
        """
        perm = CanUpdateComment()
        request = MagicMock()
        request.user.role = "INVALID"
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_can_delete_comment_fallthrough(self):
        """
        Verify comment deletion fallthrough for invalid user roles.
        """
        perm = CanDeleteComment()
        request = MagicMock()
        request.user.role = "INVALID"
        assert perm.has_object_permission(request, None, MagicMock()) is False

    def test_can_view_task_history_redundant_super_admin_block(self):
        """
        Verify that Super Admin is explicitly blocked from viewing task history.
        """
        # Even if has_permission is bypassed
        perm = CanViewTaskHistory()
        request = MagicMock()
        request.user.role = UserRoleChoices.SUPER_ADMIN
        assert perm.has_object_permission(request, None, MagicMock()) is False
        
        # Test fallthrough
        request.user.role = "INVALID"
        # Since line 282 is a direct return of the condition, we need the 
        # condition to be False (not owner and not assignee)
        obj = MagicMock()
        obj.owner = MagicMock()
        obj.assignee = MagicMock()
        assert perm.has_object_permission(request, None, obj) is False

    def test_can_restore_user_unauthenticated_fallthrough(self):
        """
        Verify that CanRestoreUser denies unauthenticated access.
        """
        perm = CanRestoreUser()
        request = MagicMock()
        request.user.is_authenticated = False
        assert perm.has_permission(request, None) is False

    def test_can_restore_user_fallthroughs(self):
        """
        Verify various fallthrough scenarios for user restoration (invalid roles, cross-org).
        """
        perm = CanRestoreUser()
        # Non-user target for Tenant Admin
        tenant_admin = MagicMock()
        tenant_admin.role = UserRoleChoices.TENANT_ADMIN
        tenant_admin.organization.is_active = True
        
        target = MagicMock()
        target.role = UserRoleChoices.TENANT_ADMIN # Not USER
        request = MagicMock()
        request.user = tenant_admin
        assert perm.has_object_permission(request, None, target) is False
        
        # Cross-org for Tenant Admin
        target.role = UserRoleChoices.USER
        target.organization = MagicMock()
        tenant_admin.organization = MagicMock()
        assert perm.has_object_permission(request, None, target) is False
        
        # Super Admin restoring non-TenantAdmin
        super_admin = MagicMock()
        super_admin.role = UserRoleChoices.SUPER_ADMIN
        request.user = super_admin
        target.role = UserRoleChoices.USER
        assert perm.has_object_permission(request, None, target) is False
        
        # Final fallthrough
        request.user.role = UserRoleChoices.USER
        assert perm.has_object_permission(request, None, target) is False

    def test_can_delete_user_fallthroughs(self):
        """
        Verify various fallthrough scenarios for user deletion (invalid roles, cross-org).
        """
        perm = CanDeleteUser()
        request = MagicMock()
        request.method = 'DELETE'
        
        # Super Admin deleting Normal User (covered but double checking)
        request.user.role = UserRoleChoices.SUPER_ADMIN
        target = MagicMock()
        target.role = UserRoleChoices.USER
        assert perm.has_object_permission(request, None, target) is False
        
        # Tenant Admin deleting Tenant Admin
        request.user.role = UserRoleChoices.TENANT_ADMIN
        target.role = UserRoleChoices.TENANT_ADMIN
        assert perm.has_object_permission(request, None, target) is False
        
        # Final fallthrough (Regular User role)
        request.user.role = UserRoleChoices.USER
        # self deletion check
        request.user = MagicMock()
        target = MagicMock() # Different
        assert perm.has_object_permission(request, None, target) is False
