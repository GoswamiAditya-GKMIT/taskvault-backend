from django.utils import timezone
from django.db import transaction
from tasks.models import Task, Comment



@transaction.atomic
def soft_delete_user(user):
    """
    Soft delete a user.
    """

    now = timezone.now()

    user.deleted_at = now
    user.save(update_fields=["deleted_at"])

    Task.objects.filter(
        deleted_at__isnull=True
    ).filter(
        owner=user
    ).update(deleted_at=now)

    Task.objects.filter(
        deleted_at__isnull=True
    ).filter(
        assignee=user
    ).update(deleted_at=now)

    Comment.objects.filter(
        user=user,
        deleted_at__isnull=True
    ).update(deleted_at=now)

