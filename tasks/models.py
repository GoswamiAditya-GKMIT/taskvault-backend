import uuid
from django.db import models
from django.conf import settings
from core.choices import TaskStatusChoices, TaskPriorityChoices

User = settings.AUTH_USER_MODEL

class Task(models.Model):
    id = models.UUIDField(primary_key=True , default=uuid.uuid4 , editable=False)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE ,
        related_name="created_tasks"
        )

    assignee = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name="assigned_tasks"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=TaskStatusChoices.choices,
        default=TaskStatusChoices.PENDING
    )

    priority = models.CharField(
        max_length=20,
        choices=TaskPriorityChoices.choices,
        default=TaskPriorityChoices.MEDIUM
    )

    deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tasks"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["assignee"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title


# task history model 
class TaskHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="history"
    )

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="task_changes"
    )

    old_status = models.CharField(
        max_length=20,
        choices=TaskStatusChoices.choices,
        null=True,
        blank=True
    )

    new_status = models.CharField(
        max_length=20,
        choices=TaskStatusChoices.choices,
        null=True,
        blank=True
    )

    old_priority = models.CharField(
        max_length=20,
        choices=TaskPriorityChoices.choices,
        null=True,
        blank=True
    )

    new_priority = models.CharField(
        max_length=20,
        choices=TaskPriorityChoices.choices,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = "tasks_history"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["actor"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"History for Task {self.task_id}"
    




# comment model
class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    user = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            related_name="comments"
    )

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)



    class Meta:
        db_table = "comments"
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.user} on {self.task}"

