from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices
from django.contrib.auth.password_validation import validate_password
from users.models import Organization
from .organization import OrganizationSerializer

User = get_user_model()


class UserCreateSerializer(serializers.Serializer):    
    email = serializers.EmailField()
    username = serializers.CharField(min_length=6, max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only = True)
    organization_id = serializers.UUIDField(required=False)

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
    
    def validate_username(self,value):

         # user can not create account with the username which is deactivated using soft delete.add
        if User.objects.filter(username=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this username, but is deleted. Please contact the administrator for account recovery."
            )
        
        # if User.objects.filter(username=value, is_email_verified=False).exists():
        #     raise serializers.ValidationError(
        #             "User verification is already pending for this username."
        #     )

        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "username already exists."
            )
        
        if value.isdigit():
            raise serializers.ValidationError(
                    "Username cannot consist of only numbers."
            )       
        return value
    
    def validate_last_name(self , value):
        if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
        return value
    
    
    def validate(self, attrs):
        request = self.context["request"]
        creator = request.user

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords do not match."]}
            )
        
        # Regular users cannot create users
        if creator.role == UserRoleChoices.USER:
            raise serializers.ValidationError("You are not allowed to create users.")

        # SUPER_ADMIN must provide organization_id
        if creator.role == UserRoleChoices.SUPER_ADMIN:
            if not attrs.get("organization_id"):
                raise serializers.ValidationError(
                    {"organization_id": "This field is required."}
                )

        # TENANT_ADMIN cannot provide organization_id
        if creator.role == UserRoleChoices.TENANT_ADMIN and attrs.get("organization_id"):
            raise serializers.ValidationError(
                {"organization_id": "Not allowed."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        creator = request.user

        validated_data.pop("confirm_password") 
        password = validated_data.pop("password")

        organization = None
        role = UserRoleChoices.USER

        if creator.role == UserRoleChoices.SUPER_ADMIN:
            org_id = validated_data.pop("organization_id", None)
            
            try:
                organization = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                # Raise validation error if ID is not found
                raise serializers.ValidationError({
                    "organization_id": "No organization found with the provided ID."
                })
            
            role = UserRoleChoices.TENANT_ADMIN

        elif creator.role == UserRoleChoices.TENANT_ADMIN:
            organization = creator.organization
            role = UserRoleChoices.USER

        user = User(
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            role=role,
            organization=organization,
            is_email_verified=False,
            is_active=False,
        )

        user.set_password(password)
        user.save()

        return user

class UserListDetailSerializer(serializers.ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'role', 
            'organization',
            'created_at', 
            'updated_at',
            'is_active', 
            'is_email_verified',
        )

class UserMiniDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying minimal user details (used in tasks).
    """
    organization = OrganizationSerializer(read_only=True)
    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name',
            'organization',
            'created_at', 


        )


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, max_length=150)
    last_name = serializers.CharField(required=False, max_length=150)
    is_active = serializers.BooleanField(required=False)

    def validate_first_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError(
                "First name must contain only alphabets."
            )
        return value

    def validate_last_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError(
                "Last name must contain only alphabets."
            )
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one field must be provided for update."
            )
    
        request_user = self.context.get("request_user")
        
        if "is_active" in attrs:
            # If the user is NOT an Admin, they cannot change is_active.
            if request_user and request_user.role != UserRoleChoices.ADMIN:
                
                # Check 1: Prevent changing the value
                if getattr(self.instance, 'is_active') != attrs['is_active']:
                    raise serializers.ValidationError({
                        "is_active": ["Only administrators can modify the 'is_active' status."]
                    })
                
                # If they tried to change it to the same value, we still remove it
                # to prevent redundant checks.
                attrs.pop("is_active")
        instance = self.instance

        changes = False
        for field, value in attrs.items():
            if getattr(instance, field) != value:
                changes = True
                break

        if not changes:
            raise serializers.ValidationError(
                "No changes detected in the update request."
            )

        return attrs

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=validated_data.keys())
        return instance
    


# only tenant admin can invite user
class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        request = self.context["request"]
        inviter = request.user

        #  Only TENANT_ADMIN can invite
        if inviter.role != UserRoleChoices.TENANT_ADMIN:
            raise serializers.ValidationError(
                "Only tenant admins can invite users."
            )

        #  Tenant admin must belong to an organization
        if not inviter.organization:
            raise serializers.ValidationError(
                "Tenant admin must belong to an organization."
            )

        #  Block already verified users
        if User.objects.filter(
            email=attrs["email"],
            deleted_at__isnull=True,
        ).exists():
            raise serializers.ValidationError(
                "A verified user with this email already exists."
            )

        return attrs
    
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Do NOT leak whether email exists
        if not User.objects.filter(
            email=value,
            is_email_verified=True,
            deleted_at__isnull=True
        ).exists():
            pass
        return value