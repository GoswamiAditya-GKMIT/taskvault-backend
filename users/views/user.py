from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model


from users.serializers.user import (
    UserListDetailSerializer,
    UserUpdateSerializer,
)
from core.permissions import IsAdmin , IsAdminOrSelf
from core.pagination import DefaultPagination
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


class UserDetailUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def get_object(self, request, id):
        user = get_object_or_404(
            User,
            id=id,
            deleted_at__isnull=True
        )
        self.check_object_permissions(request, user)
        return user

    def get(self, request, id):
        user = self.get_object(request, id)

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
        user = self.get_object(request, id)

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

    #To do - in future - admin can restore the user and all its attributes including the tasks and all
            # or admin can allow to remove the user (hard delete) and recreate the new user 
            # or can just use patch and remove all the associated item and pretend to be use the same existing user
            
    def delete(self, request, id):
        user = self.get_object(request, id)

        soft_delete_user(user)

        return Response(
            {
                "status": "success",
                "message": "User deleted successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )