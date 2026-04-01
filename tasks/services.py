from tasks.models import TaskHistory


def update_task(task, *, user, status=None, priority=None, deadline=None):
    """
    Update task and create audit history.
    """

    old_status = task.status
    old_priority = task.priority

    if status is not None:
        task.status = status

    if priority is not None:
        task.priority = priority

    if deadline is not None:
        task.deadline = deadline

    task.save()

    if old_status != task.status or old_priority != task.priority:
        TaskHistory.objects.create(
            organization=task.organization,
            task=task,
            actor=user,
            old_status=old_status,
            new_status=task.status,
            old_priority=old_priority,
            new_priority=task.priority,
        )

    return task