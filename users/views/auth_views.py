from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import RegisterSerializer , LoginSerializer , ResetPasswordSerializer , LogoutSerializer , TokenRefreshSerializer

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self , request):
        serializer = RegisterSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "status": "success",
                "message": "User registered successfully",
                "data": None,
            },
            status=status.HTTP_201_CREATED,
        )
    

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self , request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
             "status": "success",
                "message": "Login successful",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    },
            },
            status=status.HTTP_200_OK,
        )
    

class ResetPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Password changed successfully",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )



class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "status": "success",
                "message": "Logout successful",
                "data": None,
            },
            status=status.HTTP_200_OK
        )
    
    
class TokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "status": "success",
                "message": "Token refreshed successfully",
                "data": {
                    "access": serializer.validated_data["access"],
                    "refresh": serializer.validated_data["refresh"]
                },
            },
            status=status.HTTP_200_OK,
        )
    
