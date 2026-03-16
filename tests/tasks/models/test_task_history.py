import pytest
from tasks.models import TaskHistory
from tests.factories import TaskHistoryFactory, TaskFactory

@pytest.mark.django_db
class TestTaskHistoryModel:
    """
    Test suite for TaskHistory model functionality.
    """

    def test_task_history_creation_success(self):
        """
        Verify that task history is created correctly and has expected string representation.
        """
        task = TaskFactory()
        history = TaskHistoryFactory(task=task)
        
        assert history.task == task
        assert str(history) == f"History for Task {task.id}"

    def test_task_history_fields(self, active_organization, normal_user):
        """
        Verify that all fields of TaskHistory are correctly stored.
        """
        task = TaskFactory(organization=active_organization)
        history = TaskHistory.objects.create(
            organization=active_organization,
            task=task,
            actor=normal_user,
            old_status="PENDING",
            new_status="IN_PROGRESS",
            old_priority="MEDIUM",
            new_priority="HIGH"
        )
        
        assert history.old_status == "PENDING"
        assert history.new_status == "IN_PROGRESS"
        assert history.old_priority == "MEDIUM"
        assert history.new_priority == "HIGH"
        assert history.actor == normal_user
