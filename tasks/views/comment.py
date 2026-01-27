from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied



from tasks.models import Task, Comment
from tasks.serializers.comment import (
    CommentCreateUpdateSerializer,
    CommentDetailSerializer
)
from core.permissions import CanViewOrCreateComment , CanViewOrCreateComment, CanUpdateComment, CanDeleteComment
from core.pagination import DefaultPagination
from core.choices import UserRoleChoices


class TaskCommentListCreateAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
        CanViewOrCreateComment,
    ]

    def get(self, request, task_id):
        task = get_object_or_404(
            Task,
            id=task_id,
            organization=request.user.organization,
            deleted_at__isnull=True
        )

        self.check_object_permissions(request, task)

        queryset = Comment.objects.filter(
            task=task,
            deleted_at__isnull=True
        ).order_by("-created_at")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = CommentDetailSerializer(page, many=True)
            response = {
                "status": "success",
                "message": "Comments retrieved successfully",
                "data": serializer.data,
            }
            response.update(paginator.get_root_pagination_data())
            return Response(response)

        serializer = CommentDetailSerializer(queryset, many=True)
        return Response(
            {
                "status": "success",
                "message": "Comments retrieved successfully",
                "data": serializer.data,
            }
        )

    def post(self, request, task_id):
        task = get_object_or_404(
            Task, 
            id=task_id, 
            organization=request.user.organization,
            deleted_at__isnull=True
        )

        #  object-level permission
        self.check_object_permissions(request, task)

        serializer = CommentCreateUpdateSerializer(
            data=request.data,
            context={"request": request, "task": task}
        )
        serializer.is_valid(raise_exception=True)

        comment = serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Comment added successfully",
                "data": CommentDetailSerializer(comment).data,
            },
            status=status.HTTP_201_CREATED
        )


class TaskCommentDetailUpdateDeleteAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
        CanViewOrCreateComment,
        CanUpdateComment,
        CanDeleteComment,
    ]

    def get_object(self, request, task_id, comment_id):
        task = get_object_or_404(
            Task,
            id=task_id,
            organization=request.user.organization,
            deleted_at__isnull=True
        )
        comment = get_object_or_404(
            Comment,
            id=comment_id,
            task=task,
            deleted_at__isnull=True
        )
        return comment

    def get(self, request, task_id, comment_id):
        comment = self.get_object(request, task_id, comment_id)
        self.check_object_permissions(request, comment.task)

        return Response(
            {
                "status": "success",
                "message": "Comment retrieved successfully",
                "data": CommentDetailSerializer(comment).data,
            }
        )

    def patch(self, request, task_id, comment_id):
        comment = self.get_object(request, task_id, comment_id)
        self.check_object_permissions(request, comment)

        serializer = CommentCreateUpdateSerializer(
            comment,
            data=request.data,
            partial=True,
            context={"request": request, "task": comment.task}
        )
        serializer.is_valid(raise_exception=True)

        comment.message = serializer.validated_data["message"]
        comment.save(update_fields=["message"])

        return Response(
            {
                "status": "success",
                "message": "Comment updated successfully",
                "data": CommentDetailSerializer(comment).data,
            }
        )

    def delete(self, request, task_id, comment_id):
        comment = self.get_object(request, task_id, comment_id)
        self.check_object_permissions(request, comment)

        comment.deleted_at = timezone.now()
        comment.save(update_fields=["deleted_at"])

        return Response(
            {
                "status": "success",
                "message": "Comment deleted successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    
    