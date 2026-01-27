# users/serializers/organization.py
from rest_framework import serializers
from users.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    total_active_task_count = serializers.IntegerField(read_only=True)
    total_active_user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = [ "id", "created_at", "updated_at" , "deleted_at"]



    

