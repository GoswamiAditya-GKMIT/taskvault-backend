import pytest
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from tasks.serializers.task import TaskCreateSerializer, TaskUpdateSerializer
from tests.factories import TaskFactory
from tests.factories import OrganizationFactory
from tests.factories import TenantAdminFactory, NormalUserFactory
from unittest.mock import MagicMock
from core.choices import TaskStatusChoices

@pytest.mark.django_db
class TestTaskCreateSerializer:
    """
    Unit tests for TaskCreateSerializer validation logic.
    """

    def test_task_create_serializer_past_deadline(self):
        """
        Verify that creating a task with a past deadline is rejected.
        """
        serializer = TaskCreateSerializer()
        past_time = timezone.now() - timedelta(days=1)
        with pytest.raises(serializers.ValidationError) as exc:
            serializer.validate_deadline(past_time)
        assert "Deadline cannot be in the past" in str(exc.value)

    def test_task_create_serializer_nesting_limit(self):
        """
        Verify that subtasks cannot be created for existing subtasks (limit 1 level).
        """
        org = OrganizationFactory(is_active=True)
        admin = TenantAdminFactory(organization=org)
        parent = TaskFactory(organization=org, owner=admin)
        child = TaskFactory(organization=org, parent_task=parent)
        
        request = MagicMock()
        request.user = admin
        
        data = {
            "title": "Sub-subtask",
            "priority": "MEDIUM",
            "parent_task_id": str(child.id)
        }
        
        serializer = TaskCreateSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "parent_task_id" in serializer.errors
        assert "Maximum nesting level is 1" in str(serializer.errors["parent_task_id"][0])

    def test_task_create_serializer_ownership_rule_user(self):
        """
        Verify that normal users can only create subtasks for tasks they own.
        """
        org = OrganizationFactory(is_active=True)
        user = NormalUserFactory(organization=org)
        other_user = NormalUserFactory(organization=org)
        parent = TaskFactory(organization=org, owner=other_user)
        
        request = MagicMock()
        request.user = user
        
        data = {
            "title": "Subtask",
            "priority": "MEDIUM",
            "parent_task_id": str(parent.id)
        }
        
        serializer = TaskCreateSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "parent_task_id" in serializer.errors
        assert "You can only create subtasks for tasks you own" in str(serializer.errors["parent_task_id"][0])

@pytest.mark.django_db
class TestTaskUpdateSerializer:
    """
    Unit tests for TaskUpdateSerializer validation logic.
    """

    def test_task_update_serializer_complete_with_incomplete_subtasks(self):
        """
        Verify that a parent task cannot be marked COMPLETED if it has incomplete subtasks.
        """
        org = OrganizationFactory(is_active=True)
        parent = TaskFactory(organization=org, status="PENDING")
        child = TaskFactory(organization=org, parent_task=parent, status="PENDING")
        
        data = {"status": "COMPLETED"}
        serializer = TaskUpdateSerializer(instance=parent, data=data)
        assert not serializer.is_valid()
        assert "status" in serializer.errors
        assert "incomplete subtasks" in str(serializer.errors["status"][0])

    def test_task_update_serializer_no_changes(self):
        """
        Verify that updating a task without any changes in field values is rejected.
        """
        task = TaskFactory(status="PENDING")
        data = {"status": "PENDING"}
        serializer = TaskUpdateSerializer(instance=task, data=data)
        assert not serializer.is_valid()
        assert "No changes detected" in str(serializer.errors["non_field_errors"][0])
