from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied


from users.serializers.user_serializers import (
    UserListDetailSerializer,
    UserUpdateSerializer,
)
from core.permissions import IsAdmin
from core.pagination import DefaultPagination
from core.choices import UserRoleChoices
from users.service import soft_delete_user

User = get_user_model()  #getting user model inherited from abstractuser

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


    
class UserDetailUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        request_user = request.user

        user = get_object_or_404(User, id=id, deleted_at__isnull=True)

        if (request_user.role != UserRoleChoices.ADMIN and request_user != user):
            raise PermissionDenied("You do not have permission to view this user.")
        
        serializer = UserListDetailSerializer(user)
        return Response(
            {
                "status": "success",
                "message": "User retrieved successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    

    def patch(self, request, id):
        request_user = request.user

        user = get_object_or_404(
            User,
            id=id,
            deleted_at__isnull=True
        )

        if (
            request_user.role != UserRoleChoices.ADMIN
            and request_user != user
        ):
            raise PermissionDenied(
                "You do not have permission to update this user."
            )

        serializer = UserUpdateSerializer(
            instance=user,         
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save() 


        return Response(
            {
                "status": "success",
                "message": "User updated successfully",
                "data": UserListDetailSerializer(updated_user).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        request_user = request.user

        user = get_object_or_404(
            User,
            id=id,
            deleted_at__isnull=True
        )

        if (
            request_user.role != UserRoleChoices.ADMIN
            and request_user != user
        ):
            raise PermissionDenied(
                "You do not have permission to delete this user."
            )

        soft_delete_user(user)

        return Response(
            {
                "status": "success",
                "message": "User deleted successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
