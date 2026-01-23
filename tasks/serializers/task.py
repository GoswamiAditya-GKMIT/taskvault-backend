from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.choices import TaskPriorityChoices, UserRoleChoices
from tasks.models import Task
from django.db.models import functions
from django.utils import timezone
from users.serializers import UserMiniDetailSerializer
from core.choices import TaskStatusChoices, TaskPriorityChoices


User = get_user_model()

class TaskListSerializer(serializers.ModelSerializer):
    owner = UserMiniDetailSerializer(read_only=True)
    assignee = UserMiniDetailSerializer(read_only=True)
    subtasks_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            "id", "title", "status", "priority", "deadline", 
            "owner", "assignee", "organization", "parent_task",
            "created_at", "subtasks_count"
        ]
        read_only_fields = ["id", "organization", "created_at"]


class TaskDetailSerializer(serializers.ModelSerializer):
    owner = UserMiniDetailSerializer(read_only=True)
    assignee = UserMiniDetailSerializer(read_only=True)
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "priority", "deadline",
            "owner", "assignee", "organization", "parent_task",
            "created_at", "updated_at", "subtasks"
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def get_subtasks(self, obj):
        # Return direct subtasks using ListSerializer
        subtasks = obj.subtasks.filter(deleted_at__isnull=True).order_by("created_at")
        return TaskListSerializer(subtasks, many=True).data


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=TaskPriorityChoices.choices)
    deadline = serializers.DateTimeField(required=False)
    assignee_id = serializers.UUIDField(required=False)
    parent_task_id = serializers.UUIDField(required=False)

    def validate_deadline(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Deadline cannot be in the past."
            )
        return value
    
    def validate(self , attrs):
        request = self.context["request"]
        user = request.user
        organization = user.organization

        # 1. Block Super Admin
        if user.role == UserRoleChoices.SUPER_ADMIN:
             raise serializers.ValidationError("Super Admins cannot create tasks.")

        assignee_id = attrs.get("assignee_id")
        parent_task_id = attrs.get("parent_task_id")

        # 2. Validate Parent Task
        parent_task = None
        if parent_task_id:
            try:
                parent_task = Task.objects.get(
                    id=parent_task_id,
                    organization=organization,
                    deleted_at__isnull=True
                )
            except Task.DoesNotExist:
                raise serializers.ValidationError(
                    {"parent_task_id": "Parent task not found or does not belong to your organization."}
                )
            
            # Nesting Limit: 1 Level
            if parent_task.parent_task is not None:
                raise serializers.ValidationError(
                    {"parent_task_id": "Subtasks cannot have their own subtasks. Maximum nesting level is 1."}
                )
            
            # Subtask Rule:
            # User -> Can only create subtask if they OWN the parent.
            if user.role == UserRoleChoices.USER:
                if parent_task.owner != user:
                     raise serializers.ValidationError(
                        {"parent_task_id": "You can only create subtasks for tasks you own."}
                    )
            
            # Tenant Admin -> Can only create subtask if parent is Admin-owned
            if user.role == UserRoleChoices.TENANT_ADMIN:
                 if parent_task.owner.role not in [UserRoleChoices.TENANT_ADMIN, UserRoleChoices.SUPER_ADMIN]:
                      raise serializers.ValidationError(
                        {"parent_task_id": "Tenant Admins can only create subtasks for Admin-owned tasks."}
                    )


        # 3. Assignee Logic
        assignee = None

        if user.role == UserRoleChoices.USER:
            if assignee_id and str(assignee_id) != str(user.id):
                 raise serializers.ValidationError(
                    {"assignee_id": "Users can only create tasks for themselves."}
                )
            assignee = user

        elif user.role == UserRoleChoices.TENANT_ADMIN:
             if assignee_id:
                try:
                    assignee = User.objects.get(
                        id=assignee_id,
                        organization=organization, # Strict tenancy check
                        deleted_at__isnull=True,
                        is_active=True 
                    )
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        {"assignee_id": "Assignee does not exist or is not in your organization."}
                    )
             else:
                assignee = user
        else:
             # Should be caught by Super Admin block, but fallback
             raise serializers.ValidationError("Invalid user role.")
    

        # 4. Duplicate Check (Scoped to Organization + Assignee)
        title = attrs.get("title").strip()
        normalized_title = title.lower()

        duplicate_exists = Task.objects.filter(
            assignee=assignee,
            organization=organization,
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
        attrs["parent_task"] = parent_task
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        validated_data.pop("assignee_id", None)
        validated_data.pop("parent_task_id", None)

        return Task.objects.create(
            owner=user,
            organization=user.organization, # Auto-assign Org
            assignee=validated_data.pop("assignee"),
            parent_task=validated_data.pop("parent_task"),
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
    # to - do Allowing re-assigning.
    
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
                if field == "status" and new_value == TaskStatusChoices.COMPLETED:
                     # Check for incomplete subtasks
                     incomplete_subtasks = instance.subtasks.filter(
                         deleted_at__isnull=True
                     ).exclude(status=TaskStatusChoices.COMPLETED).exists()
                     
                     if incomplete_subtasks:
                         raise serializers.ValidationError(
                             {"status": "Cannot complete task because it has incomplete subtasks."}
                         )
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
