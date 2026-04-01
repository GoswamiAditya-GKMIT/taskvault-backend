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
        )

        # Filtering
        is_premium = request.query_params.get("is_premium")
        if is_premium:
            is_premium_bool = is_premium.lower() == "true"
            queryset = queryset.filter(is_premium=is_premium_bool)

        is_active = request.query_params.get("is_active")
        if is_active:
             is_active_bool = is_active.lower() == "true"
             queryset = queryset.filter(is_active=is_active_bool)

        queryset = (
            queryset
            .annotate(
                total_active_task_count=Count('tasks', filter=Q(tasks__deleted_at__isnull=True), distinct=True),
                total_active_user_count=Count('users', filter=Q(users__deleted_at__isnull=True), distinct=True),
            )
            .order_by("-created_at")
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
                {"status": "error", "message": "Organization not found.", "error": "Not Found"},
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

    def _update(self, request, id):
        organization = self.get_object(id)
        if not organization:
            return Response(
                {"status": "error", "message": "Organization not found.", "error": "Not Found"},
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

    def put(self, request, id):
        return self._update(request, id)

    def patch(self, request, id):
        return self._update(request, id)

    def delete(self, request, id):
        organization = self.get_object(id)
        if not organization:
            return Response(
                {"status": "error", "message": "Organization not found.", "error": "Not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Simply use is_active=False
        organization.is_active = False
        organization.save()

        return Response(
            {
            },
            status=status.HTTP_204_NO_CONTENT,
        )
