# users/views/organization.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsSuperAdmin
from users.serializers import OrganizationSerializer
from core.pagination import DefaultPagination
from users.models import Organization
from django.db.models import Count, Q
from django.utils import timezone


class OrganizationCreateAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        queryset = (
            Organization.objects
            .filter(deleted_at__isnull=True)
            .annotate(
                total_active_task_count=Count('tasks', filter=Q(tasks__deleted_at__isnull=True), distinct=True),
                total_active_user_count=Count('users', filter=Q(users__deleted_at__isnull=True), distinct=True),
            )
            .order_by("name")
        )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = OrganizationSerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Organizations retrieved successfully",
            "data": serializer.data,
        }

        response_data.update(paginator.get_root_pagination_data())

        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Organization created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetailAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get_object(self, id):
        try:
             # Annotate single object fetch as well
            return Organization.objects.annotate(
                total_active_task_count=Count('tasks', filter=Q(tasks__deleted_at__isnull=True), distinct=True),
                total_active_user_count=Count('users', filter=Q(users__deleted_at__isnull=True), distinct=True),
            ).get(id=id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            return None

    def get(self, request, id):
        organization = self.get_object(id)
        if not organization:
            return Response(
                {"status": "failed", "message": "Organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrganizationSerializer(organization)
        return Response(
            {
                "status": "success",
                "message": "Organization retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, id):
        organization = self.get_object(id)
        if not organization:
            return Response(
                {"status": "failed", "message": "Organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrganizationSerializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Organization updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        organization = self.get_object(id)
        if not organization:
            return Response(
                {"status": "failed", "message": "Organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Constraint: Cannot delete if users exist
        if organization.users.filter(deleted_at__isnull=True).exists():
             return Response(
                {
                    "status": "failed",
                    "message": "Cannot delete organization with associated users. Please remove them first.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Soft delete
        organization.deleted_at = timezone.now()
        organization.is_active = False # Deactivate as well
        organization.save()

        return Response(
            {
                "status": "success",
                "message": "Organization deleted successfully.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
