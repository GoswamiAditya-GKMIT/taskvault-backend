from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
import uuid
import time


from users.serializers import RegisterSerializer , LoginSerializer , ResetPasswordSerializer, LogoutSerializer , TokenRefreshSerializer , UserListDetailSerializer , ResendOTPSerializer , UserMiniDetailSerializer , InviteRegisterSerializer , LoginOTPVerifySerializer, VerifyUserTokenSerializer, ResendLoginOTPSerializer
from core.utils import generate_otp
from users.tasks import send_user_verification_otp, send_verification_link_email
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

        # Generate Verification Token
        token = uuid.uuid4().hex
        
        # Store token -> user_id in cache with 24h expiry
        cache_key = f"user_verification_token:{token}"
        # Store user_id -> token for invalidation on resend
        user_token_key = f"user_verification_active_token:{user.id}"

        cache.set(cache_key, user.id, timeout=86400) # 24 hours
        cache.set(user_token_key, token, timeout=86400) 

        verification_link = f"http://localhost:3000/verify-email?token={token}"

        send_verification_link_email.delay(user.email, verification_link)

        return Response(
            {
                "status": "success",
                "message": "Registration successful. Verification link sent to email.",
                "data": UserListDetailSerializer(user).data
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

        # Blacklist Access Token
        try:
            token = request.auth
            if token:
                jti = token.get("jti")
                exp = token.get("exp")
                
                # Calculate remaining time (TTL)
                current_time = time.time()
                ttl = exp - current_time
                
                if ttl > 0:
                    # Store in Redis
                    cache.set(f"blacklisted_access_token:{jti}", True, timeout=int(ttl))
        except Exception:
            # If token extraction fails, just proceed (token might be missing or invalid)
            pass

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
    



    

class ResendLoginOTPAPIView(APIView):
    """
    POST /auth/login/resend-otp/
    """
    permission_classes = [AllowAny]
    OTP_TTL = CACHE_TIMEOUT
    RESEND_COOLDOWN = RESEND_TIME

    def post(self, request):
        serializer = ResendLoginOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        
        cooldown_key = f"login_otp_cooldown:{user.id}"
        otp_cache_key = f"login_otp:{user.id}"

        # Rate limit resend
        if cache.get(cooldown_key):
             return Response(
                {
                    "status": "failed",
                    "message": "Please wait before requesting another OTP.",
                    "error": None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Generate NEW OTP (Replacing the old one effectively validates user wants fresh code)
        otp = generate_otp()
        
        # Overwrite the cache key -> Invalidates old OTP
        cache.set(otp_cache_key, {"otp": otp}, timeout=self.OTP_TTL)
        
        # Set cooldown
        cache.set(cooldown_key, True, timeout=self.RESEND_COOLDOWN)

        send_user_verification_otp.delay(user.email, otp)

        return Response(
            {
                "status": "success",
                "message": "A new OTP has been sent to your email.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationLinkAPIView(APIView):
    """
    POST /auth/resend-verification-link/
    """
    permission_classes = [AllowAny]
    TOKEN_TTL = 86400  # 24 hours
    RESEND_COOLDOWN = RESEND_TIME

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data) # Reusing existing serializer as it just checks email and user exists
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        
        # Check cooldown
        cooldown_key = f"user_verification_cooldown:{user.email}"
        if cache.get(cooldown_key):
             return Response(
                {
                    "status": "failed",
                    "message": "Please wait before requesting another link.",
                    "error": None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Invalidate old token if exists
        user_active_token_key = f"user_verification_active_token:{user.id}"
        old_token = cache.get(user_active_token_key)
        
        if old_token:
            cache.delete(f"user_verification_token:{old_token}")
            cache.delete(user_active_token_key)

        # Generate new token
        token = uuid.uuid4().hex
        
        cache.set(f"user_verification_token:{token}", user.id, timeout=self.TOKEN_TTL)
        cache.set(user_active_token_key, token, timeout=self.TOKEN_TTL)
        
        # Set cooldown
        cache.set(cooldown_key, True, timeout=self.RESEND_COOLDOWN)

        verification_link = f"http://localhost:3000/verify-email?token={token}"
        send_verification_link_email.delay(user.email, verification_link)

        return Response(
            {
                "status": "success",
                "message": "Verification link has been resent to your email.",
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


class VerifyUserTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyUserTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token = serializer.validated_data["token"]

        # Verify user
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])

        # Invalidate token
        cache.delete(f"user_verification_token:{token}")

        return Response(
            {
                "status": "success",
                "message": "Email verified successfully. You can now login.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    
