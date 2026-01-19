from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model




from users.serializers import RegisterSerializer , LoginSerializer , ResetPasswordSerializer , LogoutSerializer , TokenRefreshSerializer , UserListDetailSerializer , ResendOTPSerializer , VerifyEmailSerializer, UserMiniDetailSerializer , InviteRegisterSerializer , LoginOTPVerifySerializer
from core.utils import generate_otp
from users.tasks import send_user_verification_otp
from core.constants import CACHE_TIMEOUT , RESEND_TIME
from users.models import Organization
User = get_user_model()  #getting user model inherited from abstractuser


class RegisterAPIView(APIView):
    """
    POST /auth/<uuid:tenant_id>/register
    Self-registration into a tenant
    """

    permission_classes = [AllowAny]

    OTP_TTL = CACHE_TIMEOUT 

    def post(self, request , tenant_id):

        serializer = RegisterSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        otp = generate_otp()

        cache_key = f"user_verify_otp:{user.id}"
        cache.set(cache_key, {"otp": otp}, timeout=self.OTP_TTL)

        send_user_verification_otp.delay(user.email, otp)
        # response_serializer = UserMiniDetailSerializer(user)

        return Response(
            {
                "status": "success",
                "message": "Registration successful. OTP sent to email.",
                "data": None
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "status": "success",
                "message": "OTP sent to your email. Please verify to continue.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )

    
class LoginOTPVerifyAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginOTPVerifySerializer(data=request.data)
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
    


class VerifyEmailAPIView(APIView):
    """
    POST /auth/verify-email
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        otp = serializer.validated_data["otp"]

        cache_key = f"user_verify_otp:{user.email}"
        cached_data = cache.get(cache_key)

        if not cached_data:
            return Response(
                {
                    "status": "failed",
                    "message": "OTP expired or invalid.",
                    "error": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cached_data.get("otp") != otp:
            return Response(
                {
                    "status": "failed",
                    "message": "Invalid OTP.",
                    "error": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Activate user
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])
        
        # Remove OTP (one-time use)
        cache.delete(cache_key)

        response_serializer = UserListDetailSerializer(user)

        return Response(
            {
                "status": "success",
                "message": "Email verified successfully.",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    

class ResendOTPAPIView(APIView):
    """
    POST /auth/resend-otp
    """

    permission_classes = [AllowAny]

    OTP_TTL = CACHE_TIMEOUT     # 5 minutes
    RESEND_COOLDOWN = RESEND_TIME  # 1 minute

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        otp_cache_key = f"user_verify_otp:{user.email}"
        cooldown_key = f"user_otp_cooldown:{user.email}"

        # Prevent OTP spamming
        if cache.get(cooldown_key):
            return Response(
                {
                    "status": "failed",
                    "message": "Please wait before requesting another OTP.",
                    "error": None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        cached_data = cache.get(otp_cache_key)

        # If OTP exists and is still valid, reuse it
        if cached_data and "otp" in cached_data:
            return Response(
                {
                    "status": "failed",
                    "message": "Please wait before requesting another OTP.",
                    "data": None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )        
        else:
            otp = generate_otp()
            cache.set(
                otp_cache_key,
                {"otp": otp},
                timeout=self.OTP_TTL,
            )

        # Set resend cooldown
        cache.set(cooldown_key, True, timeout=self.RESEND_COOLDOWN)

        send_user_verification_otp.delay(user.email, otp)

        return Response(
            {
                "status": "success",
                "message": "OTP has been resent to your email.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    



class InviteRegisterAPIView(APIView):
    """
    POST /auth/invite/{token}/register
    """
    permission_classes = [AllowAny]
    OTP_TTL = CACHE_TIMEOUT

    def post(self, request, token):
        cache_key = f"user_invite:{token}"
        invite_data = cache.get(cache_key)

        if not invite_data:
            return Response(
                {
                    "status": "failed",
                    "message": "Invite link is invalid or expired.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InviteRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = Organization.objects.get(id=invite_data["organization_id"])

        user = User(
            email=invite_data["email"],
            username=serializer.validated_data["username"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            role=invite_data["role"],
            organization=organization,
            is_email_verified=False,
            is_active=False,
        )

        user.set_password(serializer.validated_data["password"])
        user.save()

        # Generate OTP
        otp = generate_otp()
        cache.set(f"user_verify_otp:{user.id}", {"otp": otp}, timeout=self.OTP_TTL)

        send_user_verification_otp.delay(user.email, otp)

        # Invalidate invite
        cache.delete(cache_key)

        return Response(
            {
                "status": "success",
                "message": "Account created. OTP sent to email.",
                "data": None,
            },
            status=status.HTTP_201_CREATED,
        )
    
