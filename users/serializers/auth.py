import re
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError , InvalidToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from core.choices import UserRoleChoices
from users.models import Organization
from django.core.cache import cache
from core.constants import CACHE_TIMEOUT , RESEND_TIME
from users.tasks import send_user_verification_otp
from core.utils import generate_otp

User = get_user_model()

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(min_length=6, max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    # -----------------------
    # Field-level validations
    # -----------------------

    def validate_username(self,value):

         # user can not create account with the username which is deactivated using soft delete.add
        if User.objects.filter(username=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this username, but is deleted. Please contact the administrator for account recovery."
            )
        
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "username already exists."
            )
        
        if value.isdigit():
            raise serializers.ValidationError(
                    "Username cannot consist of only numbers."
            )       
        return value

    def validate_password(self, value):
        """
        Use Django's default password validators
        """
        validate_password(value)
        return value

    def validate_email(self, value):
                
        if User.objects.filter(email=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this email address, but is deleted. Please contact the administrator for account recovery."
            )
        
        # Block verified users
        if User.objects.filter(
            email=value,
            is_email_verified=True,
            deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        # block multiple pending users
        if User.objects.filter(
            email=value,
            is_email_verified=False,
            deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError(
                "User verification is already pending for this email."
            )

        return value
    
    def validate_first_name(self ,value):
         if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
         return value
    
    def validate_last_name(self , value):
        if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
        return value

    # -----------------------
    # Object-level validation
    # -----------------------

    def validate(self, attrs):
        request = self.context["request"]
        tenant_id = request.parser_context["kwargs"].get("tenant_id")

        # Confirm password check
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        if not tenant_id:
            raise serializers.ValidationError(
                {"tenant": "X-Tenant-ID header is required."}
            )

        try:
            organization = Organization.objects.get(
                id=tenant_id,
                is_active=True
            )
        except Organization.DoesNotExist:
            raise serializers.ValidationError(
                {"organization": "Invalid or inactive organization."}
            )

        attrs["organization"] = organization
        return attrs

    # -----------------------
    # Creation
    # -----------------------

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        organization = validated_data.pop("organization")

        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=UserRoleChoices.USER,
            organization=organization,
            is_email_verified=False,
            is_active=False,
        )
        user.set_password(password)
        user.save()

        return user
    

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs["username"]
        password = attrs["password"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid username or password")

        if not check_password(password, user.password):
            raise AuthenticationFailed("Invalid username or password")

        if user.deleted_at:
            raise PermissionDenied("User account is deleted.")

        if not user.is_email_verified:
            raise PermissionDenied("Email verification pending.")

        if not user.is_active:
            raise PermissionDenied("User account inactive.")

        if user.organization and (user.organization.deleted_at or not user.organization.is_active):
             if user.role == UserRoleChoices.TENANT_ADMIN:
                  raise PermissionDenied("Your organization is deactivated please contact super admin to reactive the organization")
             else:
                  raise PermissionDenied("Your organization is deactivated")

        otp_cache_key = f"login_otp:{user.id}"
        cooldown_key = f"login_otp_cooldown:{user.id}"

        #  Rate limit resend
        if cache.get(cooldown_key):
            raise AuthenticationFailed(
                "OTP already sent. Please wait before retrying."
            )

        cached = cache.get(otp_cache_key)

        if cached:
            otp = cached["otp"]
        else:
            otp = generate_otp()
            cache.set(otp_cache_key, {"otp": otp}, timeout=CACHE_TIMEOUT)

        cache.set(cooldown_key, True, timeout=RESEND_TIME)

        send_user_verification_otp.delay(user.email, otp)

        attrs["user"] = user
        return attrs



class ResetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError(
                "New password must contain at least one special character."
            )
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": ["Current password is incorrect."]}
            )

        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": ["Passwords do not match."]}
            )

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": ["New password must be different from current password."]}
            )

        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
    

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        self.token = value
        try:
            self.token = RefreshToken(self.token)
        except TokenError:
            raise serializers.ValidationError(
                {"refresh": ["Invalid or expired refresh token."]}
            )

        return value

    def save(self):
        self.token.blacklist()




class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh_str = attrs.get("refresh")

        try:
            old_token = RefreshToken(refresh_str)
        except (TokenError, InvalidToken):
            raise serializers.ValidationError(
                {"refresh": ["Invalid, expired, or blacklisted refresh token."]}
            )

        user_id = old_token["user_id"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"refresh": ["User associated with this token does not exist."]}
            )

        old_token.blacklist()

        new_refresh = RefreshToken.for_user(user)

        return {
            "access": str(new_refresh.access_token),
            "refresh": str(new_refresh),
        }


class ResendLoginOTPSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate(self, attrs):
        username = attrs["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
             raise serializers.ValidationError(
                "User with this username does not exist."
            )

        if user.deleted_at:
             raise serializers.ValidationError("User account is deleted.")

        if not user.is_email_verified:
             raise serializers.ValidationError("Email verification pending.")

        if not user.is_active:
             raise serializers.ValidationError("User account inactive.")

        attrs["user"] = user
        return attrs




    


from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"]

        try:
            user = User.objects.get(
                email=email,
                is_email_verified=False,
                deleted_at__isnull=True,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No pending verification found for this email."
            )

        attrs["user"] = user
        return attrs


class InviteRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=6)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_username(self,value):

         # user can not create account with the username which is deactivated using soft delete.add
        if User.objects.filter(username=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this username, but is deleted. Please contact the administrator for account recovery."
            )
        
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "username already exists."
            )
        
        if value.isdigit():
            raise serializers.ValidationError(
                    "Username cannot consist of only numbers."
            )       
        return value

    def validate_password(self, value):
        validate_password(value)
        return value
    
    def validate_first_name(self ,value):
         if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
         return value
    
    def validate_last_name(self , value):
        if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs
    

class LoginOTPVerifySerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        username = attrs["username"]
        otp = attrs["otp"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid OTP or user")

        cache_key = f"login_otp:{user.id}"
        cached = cache.get(cache_key)

        if not cached:
            raise AuthenticationFailed("OTP expired or invalid")

        if cached["otp"] != otp:
            raise AuthenticationFailed("Invalid OTP")

        # One-time use
        cache.delete(cache_key)

        if user.organization and (user.organization.deleted_at or not user.organization.is_active):
             if user.role == UserRoleChoices.TENANT_ADMIN:
                  raise AuthenticationFailed("Your organization is deactivated please contact super admin to reactive the organization")
             else:
                  raise AuthenticationFailed("Your organization is deactivated")

        attrs["user"] = user
        return attrs


class VerifyUserTokenSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        token = attrs["token"]
        cache_key = f"user_verification_token:{token}"
        user_id = cache.get(cache_key)

        if not user_id:
            raise serializers.ValidationError({"token": "Invalid or expired token."})

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "User not found."})

        attrs["user"] = user
        return attrs