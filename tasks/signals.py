from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from tasks.models import Task
from core.cache import invalidate_tenant_cache

@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_task_cache(sender, instance, **kwargs):

    if instance.organization:
        invalidate_tenant_cache(instance.organization.id)
