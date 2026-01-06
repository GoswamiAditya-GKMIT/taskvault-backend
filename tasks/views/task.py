from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

from core.choices import UserRoleChoices
from core.pagination import DefaultPagination
from core.permissions import CanViewTask, CanUpdateTask, CanDeleteTask
from tasks.services import update_task
from tasks.models import Task
from tasks.serializers.task import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
)

User = get_user_model()


class TaskListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
        
        if user.role == UserRoleChoices.ADMIN:
            queryset = Task.objects.filter(deleted_at__isnull = True)

        else:
            queryset = Task.objects.filter(
                assignee=user,
                deleted_at__isnull=True
            )
    

        owner_id = request.query_params.get("owner_id")
        assignee_id = request.query_params.get("assignee_id")
        status_param = request.query_params.get("status")
        priority_param = request.query_params.get("priority")

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)

        if status_param:
            queryset = queryset.filter(status=status_param)

        if priority_param:
            queryset = queryset.filter(priority=priority_param)

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

        return Response(response_data, status=status.HTTP_200_OK)
    


class TaskDetailUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, id):
        task = get_object_or_404(Task, id=id, deleted_at__isnull=True)
        self.check_object_permissions(request, task)
        return task

    def get(self, request, id):
        self.permission_classes = [IsAuthenticated, CanViewTask]
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
        self.permission_classes = [IsAuthenticated, CanUpdateTask]
        task = self.get_object(request, id)

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
        self.permission_classes = [IsAuthenticated, CanDeleteTask]
        task = self.get_object(request, id)

        task.deleted_at = timezone.now()
        task.save(update_fields=["deleted_at"])

        return Response(
            {
                "status": "success",
                "message": "Task deleted successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    


