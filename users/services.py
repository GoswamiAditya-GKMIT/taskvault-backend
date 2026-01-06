from django.utils import timezone
from django.db import transaction
from tasks.models import Task, Comment


#To do - in future - admin can restore the user and all its attributes including the tasks and all
            # or admin can allow to remove the user (hard delete) and recreate the new user 
            # or can just use patch and remove all the associated item and pretend to be use the same existing user 
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

