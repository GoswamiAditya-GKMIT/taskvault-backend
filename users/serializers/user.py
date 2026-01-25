from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices
from django.contrib.auth.password_validation import validate_password
from users.models import Organization
from .organization import OrganizationSerializer
from django.core.cache import cache

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
        value = value.lower()
        if User.objects.filter(email=value, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "An account is registered with this email address, but is deleted. Please contact the administrator for account recovery."
            )
        return value
    
    def validate_first_name(self ,value):
         if not value.isalpha():
            raise serializers.ValidationError(
                    "it should only contain alphabets"
            )
         return value
    
    def validate_username(self, value):
        if value.isdigit():
            raise serializers.ValidationError("Username cannot consist of only numbers.")

        existing_user = User.objects.filter(username__iexact=value).first()
        if existing_user and existing_user.deleted_at is not None:
             raise serializers.ValidationError("Account is deleted. Contact admin.")
            
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
        
        email = attrs.get("email").lower()
        username = attrs.get("username")

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
    
        # ---------------------------------------------------
        # Uniqueness & Stale User Logic
        
        existing_user_by_email = User.objects.filter(email=email, deleted_at__isnull=True).first()
        existing_user_by_username = User.objects.filter(username__iexact=username, deleted_at__isnull=True).first()

        stale_user = None

        if existing_user_by_email:
            # Check if Verified
            if existing_user_by_email.is_email_verified:
                 raise serializers.ValidationError({"email": "A user with this email already exists."})
            
            # Check Token Active
            token_key = f"user_verification_active_token:{existing_user_by_email.id}"
            if cache.get(token_key):
                 raise serializers.ValidationError({"email": "User verification is already pending for this email."})
            
            
            stale_user = existing_user_by_email

        if existing_user_by_username:
            if stale_user and existing_user_by_username.id == stale_user.id:
                pass 
            else:
                raise serializers.ValidationError({"username": "Username already exists."})

        self.context["stale_user"] = stale_user
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
                raise serializers.ValidationError({
                    "organization_id": "No organization found with the provided ID."
                })
            
            if not organization.is_active:
                 raise serializers.ValidationError({
                    "organization_id": "Cannot create Tenant Admin for a deactivated organization."
                })
            
            role = UserRoleChoices.TENANT_ADMIN

        elif creator.role == UserRoleChoices.TENANT_ADMIN:
            organization = creator.organization
            role = UserRoleChoices.USER

        stale_user = self.context.get("stale_user")

        if stale_user:
            # OVERWRITE
            user = stale_user
            user.username = validated_data["username"]
            user.first_name = validated_data["first_name"]
            user.last_name = validated_data["last_name"]
            user.email = validated_data["email"]
            user.role = role
            user.organization = organization
            user.is_email_verified = False 
            user.is_active = False 
            user.set_password(password)
            user.save()
            return user
        else:
            # CREATE NEW
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
            'is_active', 
            'is_email_verified',
            'created_at', 
            'updated_at',
            'deleted_at'
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
            is_allowed = False
            if request_user:
                if request_user.role == UserRoleChoices.TENANT_ADMIN:
                    is_allowed = True
                elif request_user.role == UserRoleChoices.SUPER_ADMIN:
                    # Super Admin can only modify Tenant Admin
                    if self.instance.role == UserRoleChoices.TENANT_ADMIN:
                        is_allowed = True

            if not is_allowed:
                # Check 1: Prevent changing the value
                if getattr(self.instance, 'is_active') != attrs['is_active']:
                    raise serializers.ValidationError({
                        "is_active": ["Only tenant admins can modify the 'is_active' status."]
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

        #  Check for existing user
        existing_user = User.objects.filter(
            email=attrs["email"],
            deleted_at__isnull=True,
        ).first()

        if existing_user:
            # Block Verified
            if existing_user.is_email_verified:
                raise serializers.ValidationError(
                    "A verified user with this email already exists."
                )
            
            # Block Pending (Active Token)
            token_key = f"user_verification_active_token:{existing_user.id}"
            if cache.get(token_key):
                 raise serializers.ValidationError(
                    "User verification is already pending for this email."
                )
            
            # Allow Stale (Unverified + No Token) -> Proceed to send invite which will overwrite on accept
            pass

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