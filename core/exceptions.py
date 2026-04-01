from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    PermissionDenied,
    MethodNotAllowed,
    NotFound
)
from django.http import JsonResponse



def custom_api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "status": "error",
                "message": "Internal server error",
                "error": {
                    "detail": str(exc),
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        message = "Validation failed"
    elif isinstance(exc, AuthenticationFailed):
        message = "Authentication failed"
    elif isinstance(exc, PermissionDenied):
        message = "Permission denied"
    elif isinstance(exc, MethodNotAllowed):
        message = "Method not allowed"
    else:
        message = str(exc)

    custom_response_data = {
        "status": "error",
        "message": message,
        "error": response.data,
    }

    response.data = custom_response_data
    return response




def custom_404_handler(request, exception):
    return JsonResponse(
        {
            "status": "error",
            "message": "Resource not found",
            "error": {
                "detail": "The requested resources does not exist."
            },
        },
        status=404,
    )

