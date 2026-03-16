import pytest
from tasks.models import Task
from tests.factories import TaskFactory, OrganizationFactory, NormalUserFactory
from core.choices import TaskStatusChoices, TaskPriorityChoices

@pytest.mark.django_db
class TestTaskModel:
    """
    Test suite for Task model basic functionality and defaults.
    """

    def test_task_creation_success(self):
        """
        Verify that a task can be created and has correct string representation.
        """
        task = TaskFactory(title="Critical Bug")
        assert task.title == "Critical Bug"
        assert str(task) == "Critical Bug"

    def test_task_default_values(self, active_organization, normal_user):
        """
        Verify that a new task has the expected default status and priority.
        """
        # Create assignee
        assignee = NormalUserFactory(organization=active_organization)
        
        task = Task.objects.create(
            organization=active_organization,
            owner=normal_user,
            assignee=assignee,
            title="Default Task"
        )
        assert task.status == TaskStatusChoices.PENDING
        assert task.priority == TaskPriorityChoices.MEDIUM

    def test_subtask_relationship(self):
        """
        Verify the self-referential parent-child relationship for tasks.
        """
        parent = TaskFactory(title="Parent Task")
        child = TaskFactory(title="Child Task", parent_task=parent)
        
        assert child.parent_task == parent
        assert parent.subtasks.filter(id=child.id).exists()
