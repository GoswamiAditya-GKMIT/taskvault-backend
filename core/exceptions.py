from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response({
            "status": "error",
            "message": "An unexpected server error occurred.",
            "errors": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    custom_response_data = {
        "status": "error",
        "message": "Validation failed" if response.status_code == 400 else "Authentication failed" if response.status_code == 401 else str(exc),
        "errors": response.data 
    }

    response.data = custom_response_data
    return response


