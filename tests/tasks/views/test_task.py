import pytest
from rest_framework import status
from django.urls import reverse
from tasks.models import Task, TaskHistory
from tests.factories import TaskFactory
from tests.factories import TenantAdminFactory, NormalUserFactory
from tests.factories import TaskPayloadFactory

@pytest.mark.django_db
class TestTaskCRUDAPI:
    """
    Test suite for Task lifecycle management including creation, retrieval, and soft-deletion.
    """

    def test_create_task_tenant_admin_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can create a task within their organization.
        """
        url = reverse('task-list-create')
        payload = TaskPayloadFactory(assignee_id=str(tenantadmin_user.id))
        
        response = tenantadmin_client.post(url, payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Task.objects.filter(title=payload["title"]).exists()

    def test_list_tasks_tenancy_isolation(self, tenantadmin_client, tenantadmin_user, user_client, normal_user):
        """
        Verify that users only see tasks belonging to their organization and assigned/owned by them.
        """
        # Ensure they are in the same organization
        normal_user.organization = tenantadmin_user.organization
        normal_user.save()

        task_a = TaskFactory(organization=tenantadmin_user.organization, owner=tenantadmin_user, assignee=normal_user)
        other_tenant_admin = TenantAdminFactory()
        task_b = TaskFactory(organization=other_tenant_admin.organization)

        # Tenant Admin A sees their org's tasks
        url = reverse('task-list-create')
        response = tenantadmin_client.get(url)
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["id"] == str(task_a.id)

        # Normal User sees assigned task
        response_user = user_client.get(url)
        assert len(response_user.data["data"]) == 1

    def test_update_task_unauthorized_leakage(self, user_client, normal_user):
        """
        Verify that a user cannot update a task they do not own and are not assigned to.
        """
        org = normal_user.organization
        unrelated_user = NormalUserFactory(organization=org)
        task = TaskFactory(organization=org, owner=unrelated_user, assignee=unrelated_user)

        url = reverse('task-detail', kwargs={'id': task.id})
        response = user_client.patch(url, {"status": "IN_PROGRESS"})
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_soft_delete_task_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can soft-delete a task in their organization.
        """
        task = TaskFactory(organization=tenantadmin_user.organization)
        url = reverse('task-detail', kwargs={'id': task.id})
        
        response = tenantadmin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        task.refresh_from_db()
        assert task.deleted_at is not None

    def test_delete_task_with_active_subtasks_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a task cannot be deleted if it has active subtasks.
        """
        parent = TaskFactory(organization=tenantadmin_user.organization)
        child = TaskFactory(organization=tenantadmin_user.organization, parent_task=parent)
        url = reverse('task-detail', kwargs={'id': parent.id})
        
        response = tenantadmin_client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active subtasks" in str(response.data["message"])

    def test_update_deleted_task_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a deleted task cannot be updated.
        """
        from django.utils import timezone
        task = TaskFactory(organization=tenantadmin_user.organization, deleted_at=timezone.now())
        url = reverse('task-detail', kwargs={'id': task.id})
        
        response = tenantadmin_client.patch(url, {"title": "Restored?"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_task_free_tier_limit(self, tenantadmin_client, tenantadmin_user, mocker):
        """
        Verify that a free tier organization cannot exceed the task limit.
        """
        org = tenantadmin_user.organization
        org.is_premium = False
        org.save()
        
        # Mock count to exceed limit
        mocker.patch('tasks.serializers.task.Task.objects.filter', return_value=mocker.Mock(count=mocker.Mock(return_value=100)))
        
        url = reverse('task-list-create')
        payload = TaskPayloadFactory()
        
        response = tenantadmin_client.post(url, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "upgrade to premium" in str(response.data["error"]["detail"])

    def test_task_api_super_admin_forbidden(self, superadmin_client):
        """
        Verify that Super Admin is forbidden from task management.
        """
        url = reverse('task-list-create')
        assert superadmin_client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert superadmin_client.post(url, {}).status_code == status.HTTP_403_FORBIDDEN

    def test_task_api_inactive_organization_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that users in an inactive organization are forbidden from task management.
        """
        org = tenantadmin_user.organization
        org.is_active = False
        org.save()
        
        url = reverse('task-list-create')
        assert tenantadmin_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_task_detail_super_admin_forbidden(self, superadmin_client):
        """
        Verify that Super Admin is forbidden from viewing task details.
        """
        task = TaskFactory()
        url = reverse('task-detail', kwargs={'id': task.id})
        assert superadmin_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_task_detail_inactive_org_forbidden(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that users in an inactive organization are forbidden from viewing task details.
        """
        task = TaskFactory(organization=tenantadmin_user.organization)
        tenantadmin_user.organization.is_active = False
        tenantadmin_user.organization.save()
        
        url = reverse('task-detail', kwargs={'id': task.id})
        assert tenantadmin_client.get(url).status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestTaskHistoryAPI:
    """
    Test suite for automated Task History tracking.
    """

    def test_task_history_on_status_change(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that updating a task's status triggers a history log entry.
        """
        task = TaskFactory(organization=tenantadmin_user.organization, status="PENDING")
        url = reverse('task-detail', kwargs={'id': task.id})
        
        tenantadmin_client.patch(url, {"status": "COMPLETED"})
        
        history_url = reverse('task-history', kwargs={'task_id': task.id})
        response = tenantadmin_client.get(history_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) >= 1
        assert response.data["data"][0]["old_status"] == "PENDING"
        assert response.data["data"][0]["new_status"] == "COMPLETED"

    def test_task_history_super_admin_forbidden(self, superadmin_client):
        """
        Verify that Super Admin cannot view task history.
        """
        task = TaskFactory()
        url = reverse('task-history', kwargs={'task_id': task.id})
        response = superadmin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


