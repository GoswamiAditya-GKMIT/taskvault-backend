from rest_framework import serializers
from tasks.models import TaskHistory
from users.serializers import UserMiniDetailSerializer


class TaskHistorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    old_status = serializers.CharField(allow_null=True)
    new_status = serializers.CharField(allow_null=True)
    old_priority = serializers.CharField(allow_null=True)
    new_priority = serializers.CharField(allow_null=True)

    actor = UserMiniDetailSerializer(allow_null=True)

    created_at = serializers.DateTimeField()
