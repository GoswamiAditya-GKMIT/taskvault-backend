from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from core.choices import UserRoleChoices
from core.pagination import DefaultPagination
from tasks.models import Task, TaskHistory
from tasks.serializers.history import TaskHistorySerializer
from core.permissions import CanViewTaskHistory


class TaskHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, CanViewTaskHistory]

    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, deleted_at__isnull=True)

        # object-level permission
        self.check_object_permissions(request, task)

        queryset = TaskHistory.objects.filter(task=task).order_by("-created_at")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = TaskHistorySerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Task history retrieved successfully",
            "data": serializer.data,
        }

        response_data.update(paginator.get_root_pagination_data())

        return Response(response_data, status=status.HTTP_200_OK)
