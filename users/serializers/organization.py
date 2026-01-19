# users/serializers/organization.py
from rest_framework import serializers
from users.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = [ "id", "created_at", "updated_at" , "deleted_at"]



    

