from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from core.choices import UserRoleChoices
from core.pagination import DefaultPagination
from tasks.models import Task, TaskHistory
from tasks.serializers.history_serializers import TaskHistorySerializer


class TaskHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        user = request.user

        task = get_object_or_404(Task, id=task_id, deleted_at__isnull=True)

        if user.role != UserRoleChoices.ADMIN and task.assignee != user:
            raise PermissionDenied("You do not have permission to view task history.")

        queryset = TaskHistory.objects.filter(task=task)

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
