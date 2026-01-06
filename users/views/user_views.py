from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from users.serializers.user_serializers import (
    UserListDetailSerializer,
    # UserUpdateSerializer,
)
from core.permissions import IsAdmin
from core.pagination import DefaultPagination

User = get_user_model()

class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        queryset = (
            User.objects
            .filter(deleted_at__isnull=True)
            .order_by("first_name", "last_name")
        )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = UserListDetailSerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Users retrieved successfully",
            "data": serializer.data,
        }

        response_data.update(paginator.get_root_pagination_data())

        return Response(response_data, status=status.HTTP_200_OK)


class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserListDetailSerializer(request.user)
        return Response(
            {
                "status": "success",
                "message": "Profile retrieved successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, id):
        user = get_object_or_404(User, id=id, deleted_at__isnull=True)

        serializer = UserListDetailSerializer(user)
        return Response(
            {
                "status": "success",
                "message": "User retrieved successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    
