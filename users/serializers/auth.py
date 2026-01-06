import re
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError , InvalidToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

User = get_user_model()

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=6 , max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only =True , min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        """
        Password must contain at least one special character.
        """
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError(
                "Password must contain at least one special character."
            )
        return value
    
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
        
    def validate_first_name(self ,value):
         if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
         return value

    def validate_email(self, value):
        value = value.lower()

        # user can not create account with the username which is deactivated using soft delete.add

        if User.objects.filter(email=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this email address, but is deleted. Please contact the administrator for account recovery."
            )
        
        if User.objects.filter(email = value).exists():
            raise serializers.ValidationError(
                    "email already exists."
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
                {"confirm_password": ["Passwords do not match."]}
            )
        return attrs

    
    def create(self ,validated_data):
        validated_data.pop("confirm_password") 

        user = User(
            username = validated_data["username"],
            first_name = validated_data["first_name"],
            last_name = validated_data["last_name"],
            email = validated_data["email"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only = True)

    def validate(self, attrs):
        username = attrs["username"]
        password = attrs["password"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid username or password")
            
        if not check_password(password, user.password):
            raise serializers.ValidationError("Invalid username or password")
        
        if user.deleted_at:
            raise serializers.ValidationError(
                "User account is deleted. Contact admin to re-activate the account."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "User account is temporary inactive. Do contact admin to re-activate the account."
            )
        
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
