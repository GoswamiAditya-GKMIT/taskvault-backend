from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.contrib.auth.hashers import make_password


from users.serializers import RegisterSerializer , LoginSerializer , ResetPasswordSerializer , LogoutSerializer , TokenRefreshSerializer , UserListDetailSerializer

from core.utils import generate_otp
from users.tasks import send_otp_email
from core.constants import CACHE_TIMEOUT
from users.models import User



class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        cache_key = f"register_{email}"
        if cache.get(cache_key):
            return Response({"status":"Failed",
                             "message": "OTP already sent. Please verify.",
                             "data":None}, status=400)

        otp = generate_otp()

        redis_data = serializer.validated_data
        redis_data.pop("confirm_password")                 # remove it
        redis_data["password"] = make_password(redis_data["password"])  # storing hashed password in redis cache
        redis_data["otp"] = otp

        cache.set(cache_key, redis_data, timeout=CACHE_TIMEOUT) # cache timeout value from the core/constants

        send_otp_email.delay(email, otp)

        return Response({
            "status": "success",
            "message": "OTP sent to email. Please verify.",
            "data":None
        }, status=200)

class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        cache_key = f"register_{email}"
        data = cache.get(cache_key)

        if not email:
            return Response({            
                "status": "Failed",
                "message": "Please Provide respective Email",
                "data": None}, status=400)
        if not otp:
            return Response({
                "status": "Failed",
                "message": "OTP is missing",
                "data": None}, status=400)
        
        if not data:
            return Response({ "status": "Failed",
                              "message": "OTP expired",
                              "data":None}, status=400)

        if data["otp"] != otp:
            return Response({ "status": "Failed",
                              "message": "Invalid OTP",
                              "data":None}, status=400)

        # Create user
        user = User.objects.create(
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            password=data["password"],   # already hashed
        )
        response_serializer =  UserListDetailSerializer(user)
        cache.delete(cache_key)

        return Response({
            "status": "success",
            "message": "Account created successfully",
            "data": response_serializer.data
        }, status=201)



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
        user_instance = serializer.save()
        response_serializer = UserListDetailSerializer(user_instance)

        return Response(
            {
                "status": "success",
                "message": "Password changed successfully",
                "data": response_serializer.data,
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
    
