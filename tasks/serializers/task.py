from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.choices import TaskPriorityChoices, UserRoleChoices
from tasks.models import Task
from django.db.models import functions
from django.utils import timezone
from users.serializers import UserMiniDetailSerializer
from core.choices import TaskStatusChoices, TaskPriorityChoices


User = get_user_model()

class TaskListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    owner = UserMiniDetailSerializer(read_only=True)
    assignee = UserMiniDetailSerializer(read_only=True)
    created_at = serializers.DateTimeField()


class TaskDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    deadline = serializers.DateTimeField(allow_null=True)

    owner = UserMiniDetailSerializer(read_only=True)
    assignee = UserMiniDetailSerializer(read_only=True)

    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=TaskPriorityChoices.choices)
    deadline = serializers.DateTimeField(required=False)
    assignee_id = serializers.UUIDField(required=False)

    def validate_deadline(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Deadline cannot be in the past."
            )
        return value
    
    def validate(self , attrs):
        request = self.context["request"]
        user = request.user

        assignee_id = attrs.get("assignee_id")

        if user.role == UserRoleChoices.USER:
            if assignee_id and assignee_id != user.id:
                raise serializers.ValidationError(
                    "Users can only create tasks for themselves."
                )
            assignee = user

        elif user.role == UserRoleChoices.ADMIN:
            if assignee_id:
                try:
                    assignee = User.objects.get(
                        id=assignee_id,
                        deleted_at__isnull=True
                    )
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        {"assignee_id": "Assignee does not exist."}
                    )
            else:
                assignee = user

        else:
            raise serializers.ValidationError("Invalid user role.")
    

        title = attrs.get("title").strip()
        normalized_title = title.lower()

        duplicate_exists = Task.objects.filter(
            # owner=user,
            assignee=assignee,
            deleted_at__isnull=True,
        ).annotate(
            normalized_db_title=functions.Lower("title")
        ).filter(
            normalized_db_title=normalized_title
        ).exists()

        if duplicate_exists:
            raise serializers.ValidationError(
                {
                    "title": "Task with this title already exists for this user."
                }
            )

        attrs["title"] = title
        attrs["assignee"] = assignee
        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        validated_data.pop("assignee_id", None)

        return Task.objects.create(
            owner=request.user,
            assignee=validated_data.pop("assignee"),
            **validated_data
        )


class TaskUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=TaskStatusChoices.choices,
        required=False
    )
    priority = serializers.ChoiceField(
        choices=TaskPriorityChoices.choices,
        required=False
    )
    deadline = serializers.DateTimeField(required=False)

    def validate_deadline(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Deadline cannot be in the past."
            )
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one field must be provided to update."
            )
        
        instance = self.instance
        if not instance:
            return attrs

        has_change = False

        for field, new_value in attrs.items():
            old_value = getattr(instance, field)

            if old_value != new_value:
                has_change = True
                break

        if not has_change:
            raise serializers.ValidationError(
                "No changes detected. Please modify at least one field."
            )

        return attrs

    def update(self, instance, validated_data):
        for field in ["status", "priority", "deadline"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance
    

