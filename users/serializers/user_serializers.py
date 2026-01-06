from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()
class UserListDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()

class UserMiniDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, max_length=150)
    last_name = serializers.CharField(required=False, max_length=150)

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