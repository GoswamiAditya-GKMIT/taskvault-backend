from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.choices import UserRoleChoices

User = get_user_model()
class UserListDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'role', 
            'created_at', 
            'updated_at',
            'is_active', 
        )

class UserMiniDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying minimal user details (used in tasks).
    """
    class Meta:
        model = User
        fields = (
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name'
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