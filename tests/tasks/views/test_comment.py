import pytest
from rest_framework import status
from django.urls import reverse
from tests.factories import TaskFactory, CommentFactory
from tests.factories import NormalUserFactory, TenantAdminFactory

@pytest.mark.django_db
class TestCommentAPI:
    """
    Test suite for task comment lifecycle and permission logic.
    """

    def test_create_comment_success(self, user_client, normal_user):
        """
        Verify that a user can successfully comment on a task they have access to.
        """
        task = TaskFactory(organization=normal_user.organization, owner=normal_user)
        url = reverse('comment-list-create', kwargs={'task_id': task.id})
        payload = {"message": "Looking into this"}
        
        response = user_client.post(url, payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["message"] == "Looking into this"

    def test_create_comment_unauthorized_task_forbidden(self, user_client):
        """
        Verify that a user cannot comment on a task that belongs to another organization.
        """
        other_task = TaskFactory() # Different org
        url = reverse('comment-list-create', kwargs={'task_id': other_task.id})
        payload = {"message": "Illegal comment"}
        
        response = user_client.post(url, payload)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND # Task not found in queryset

    def test_list_comments_visibility(self, user_client, normal_user):
        """
        Verify that a user can list comments for a task they have access to.
        """
        task = TaskFactory(organization=normal_user.organization, owner=normal_user)
        CommentFactory(task=task, user=normal_user, organization=normal_user.organization)
        
        url = reverse('comment-list-create', kwargs={'task_id': task.id})
        response = user_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1

    def test_update_comment_self_success(self, user_client, normal_user):
        """
        Verify that a user can update their own comment.
        """
        task = TaskFactory(organization=normal_user.organization, owner=normal_user)
        comment = CommentFactory(task=task, user=normal_user, organization=normal_user.organization)
        
        url = reverse('comment-detail-update-delete', kwargs={'task_id': task.id, 'comment_id': comment.id})
        response = user_client.patch(url, {"message": "Updated comment"})
        
        assert response.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.message == "Updated comment"

    def test_update_comment_other_forbidden(self, user_client, normal_user):
        """
        Verify that a user cannot update another user's comment.
        """
        task = TaskFactory(organization=normal_user.organization, owner=normal_user)
        other_user = NormalUserFactory(organization=normal_user.organization)
        other_comment = CommentFactory(task=task, user=other_user, organization=normal_user.organization)
        
        url = reverse('comment-detail-update-delete', kwargs={'task_id': task.id, 'comment_id': other_comment.id})
        response = user_client.patch(url, {"message": "Hacked"})
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_comment_tenant_admin_success(self, tenantadmin_client, tenantadmin_user):
        """
        Verify that a Tenant Admin can delete any comment within their organization's tasks.
        """
        normal_user = NormalUserFactory(organization=tenantadmin_user.organization)
        task = TaskFactory(organization=tenantadmin_user.organization, owner=normal_user)
        comment = CommentFactory(task=task, user=normal_user, organization=tenantadmin_user.organization)
        
        url = reverse('comment-detail-update-delete', kwargs={'task_id': task.id, 'comment_id': comment.id})
        response = tenantadmin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        comment.refresh_from_db()
        assert comment.deleted_at is not None

    def test_create_comment_on_deleted_task_forbidden(self, user_client, normal_user):
        """
        Verify that a user cannot comment on a soft-deleted task.
        """
        from django.utils import timezone
        task = TaskFactory(organization=normal_user.organization, owner=normal_user, deleted_at=timezone.now())
        url = reverse('comment-list-create', kwargs={'task_id': task.id})
        
        response = user_client.post(url, {"message": "Trying to comment"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_comment_on_deleted_task_forbidden(self, user_client, normal_user):
        """
        Verify that a user cannot update a comment if the parent task is deleted.
        """
        from django.utils import timezone
        task = TaskFactory(organization=normal_user.organization, owner=normal_user)
        comment = CommentFactory(task=task, user=normal_user, organization=normal_user.organization)
        task.deleted_at = timezone.now()
        task.save()
        
        url = reverse('comment-detail-update-delete', kwargs={'task_id': task.id, 'comment_id': comment.id})
        response = user_client.patch(url, {"message": "Updating comment on deleted task"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_comment_api_super_admin_forbidden(self, superadmin_client):
        """
        Verify that Super Admin is forbidden from commenting.
        """
        task = TaskFactory()
        url = reverse('comment-list-create', kwargs={'task_id': task.id})
        response = superadmin_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        response = superadmin_client.post(url, {"message": "Illegal"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
