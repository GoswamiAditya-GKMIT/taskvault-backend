# users/views/organization.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsSuperAdmin
from users.serializers import OrganizationSerializer
from core.pagination import DefaultPagination
from users.models import Organization

class OrganizationCreateAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        queryset = (
            Organization.objects
            .filter(deleted_at__isnull=True)
            .order_by("name")
        )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = OrganizationSerializer(page, many=True)

        response_data = {
            "status": "success",
            "message": "Users retrieved successfully",
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
