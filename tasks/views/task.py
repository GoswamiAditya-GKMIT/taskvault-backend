from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils import timezone
from django.db.models import Count, Q
from django.core.cache import cache
from core.cache import generate_cache_key

from core.choices import UserRoleChoices
from core.pagination import DefaultPagination
from core.permissions import CanViewTask, CanUpdateTask, CanDeleteTask, CanCreateTask
from tasks.services import update_task
from core.constants import TASK_CACHE_TIMEOUT
from tasks.models import Task
from tasks.serializers.task import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
)

User = get_user_model()


class TaskListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, CanCreateTask, CanViewTask]

    def post(self, request):
        serializer = TaskCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        response_serializer = TaskDetailSerializer(task)


        return Response(
            {
                "status": "success",
                "message": "Task created successfully",
                "data": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        user = request.user
        organization = user.organization
        
        # Try to get data from cache


        cache_key = generate_cache_key(user, self, request)
        if cache_key:
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)

        # Base QuerySet: All active tasks in the User's Organization
        # (Implicit Multi-Tenancy Filter)
        queryset = Task.objects.filter(
            organization=organization
        ).annotate(
            subtasks_count=Count(
                "subtasks", 
                filter=Q(subtasks__deleted_at__isnull=True)
            )
        ).select_related("owner", "assignee")

        # FILTER: Hide deleted tasks for non-Admins
        if user.role != UserRoleChoices.TENANT_ADMIN:
            queryset = queryset.filter(deleted_at__isnull=True)

        # FILTER: Normal Users only see tasks they own or are assigned to.
        if user.role == UserRoleChoices.USER:
            queryset = queryset.filter(
                Q(owner=user) | Q(assignee=user)
            )
    

        owner_id = request.query_params.get("owner_id")
        assignee_id = request.query_params.get("assignee_id")
        status_param = request.query_params.get("status")
        priority_param = request.query_params.get("priority")
        parent_task_id = request.query_params.get("parent_task_id")

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)

        if status_param:
            queryset = queryset.filter(status=status_param)

        if priority_param:
            queryset = queryset.filter(priority=priority_param)
            
        if parent_task_id:
            queryset = queryset.filter(parent_task_id=parent_task_id)

        queryset = queryset.order_by("-created_at")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = TaskListSerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Tasks retrieved successfully",
            "data": serializer.data,
        }

                                                                                                            
        response_data.update(paginator.get_root_pagination_data())

        # Set cache
        if cache_key:
            # Cache for 1 hour by default, invalidation handles updates
            cache.set(cache_key, response_data, timeout=TASK_CACHE_TIMEOUT)

        return Response(response_data, status=status.HTTP_200_OK)
    


class TaskDetailUpdateDeleteAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
        CanViewTask,
        CanUpdateTask,
        CanDeleteTask,
    ]

    def get_object(self, request, id):
        query = Q(organization=request.user.organization)
        
        # Hide deleted checks for non-admins
        if request.user.role != UserRoleChoices.TENANT_ADMIN:
             query &= Q(deleted_at__isnull=True)
        # Admins can see deleted tasks (no filter needed)

        task = get_object_or_404(
            Task,
            query,
            id=id
        )
        self.check_object_permissions(request, task)
        return task

    def get(self, request, id):
        task = self.get_object(request, id)

        return Response(
            {
                "status": "success",
                "message": "Task retrieved successfully",
                "data": TaskDetailSerializer(task).data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, id):
        task = self.get_object(request, id)
        
        # Block updates on deleted tasks
        if task.deleted_at:
             return Response(
                {"status": "error", "message": "Cannot update a deleted task.", "error": "Not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TaskUpdateSerializer(
            task,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        task = update_task(
            task,
            user=request.user,
            **serializer.validated_data
        )

        return Response(
            {
                "status": "success",
                "message": "Task updated successfully",
                "data": TaskDetailSerializer(task).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        task = self.get_object(request, id)
        
        # Prevent deletion if active subtasks exist
        if task.subtasks.filter(deleted_at__isnull=True).exists():
            return Response(
                {
                    "status": "error",
                    "message": "Cannot delete task because it has active subtasks.",
                    "error": "Conflict",
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        task.deleted_at = timezone.now()
        task.save(update_fields=["deleted_at"])

        return Response(
            {
            },
            status=status.HTTP_204_NO_CONTENT,
        )