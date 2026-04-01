# users/serializers/organization.py
from rest_framework import serializers
from users.models import Organization
import re


class OrganizationSerializer(serializers.ModelSerializer):
    total_active_task_count = serializers.IntegerField(read_only=True)
    total_active_user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = [ "id", "created_at", "updated_at" , "deleted_at"]

    def validate_name(self, value):
        
        # 1. Regex Validation
        if not re.match(r"^[a-zA-Z0-9 .&'-]+$", value):
             raise serializers.ValidationError("Organization name contains invalid characters. Allowed: Letters, numbers, spaces, dots (.), ampersands (&), hyphens (-), and apostrophes (').")

        # 2. Normalization (Whitespace)
        normalized_name = " ".join(value.split())
        
        # 3. Duplicate Check (Case-Insensitive & Normalized)
        # Exclude self if updating
        queryset = Organization.objects.filter(name__iexact=normalized_name)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
             raise serializers.ValidationError(f"Organization with name '{normalized_name}' already exists.")

        return value



    

