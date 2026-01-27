from django.utils import timezone
from django.db import transaction
from tasks.models import Task, Comment

@transaction.atomic
def soft_delete_user(user, actor):
    """
    Soft delete a user with atomic transaction and cascading logic.
    Tracks who performed the deletion (self vs admin).
    """
    deletion_time = timezone.now()
    
    user.deleted_at = deletion_time
    user.is_active = False
    user.deleted_by = 'self' if actor.id == user.id else 'admin'
    user.save(update_fields=['deleted_at', 'is_active', 'deleted_by'])

    # Cascading Soft Delete (Exact Timestamp)
    # Only delete items that are NOT already deleted
    # We focus on items OWNED by the user (created by them)
    Task.objects.filter(owner=user, deleted_at__isnull=True).update(deleted_at=deletion_time)
    Task.objects.filter(assignee=user, deleted_at__isnull=True).update(deleted_at=deletion_time)
    Comment.objects.filter(user=user, deleted_at__isnull=True).update(deleted_at=deletion_time)

    return user

@transaction.atomic
def restore_user(user):
    """
    Restore a user and their associated data (tasks, comments) 
    that were deleted at the same time as the user.
    """
    restore_target_time = user.deleted_at
    
    if not restore_target_time:
         return user

    user.deleted_at = None
    user.is_active = True
    user.deleted_by = None
    user.save(update_fields=['deleted_at', 'is_active', 'deleted_by'])

    # Cascade Restore (Match Timestamp)
    # Only restore items that match the user's deletion time exactly
    Task.objects.filter(owner=user, deleted_at=restore_target_time).update(deleted_at=None)
    Task.objects.filter(assignee=user, deleted_at=restore_target_time).update(deleted_at=None)
    Comment.objects.filter(user=user, deleted_at=restore_target_time).update(deleted_at=None)
    
    return user
