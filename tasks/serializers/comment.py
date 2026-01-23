from rest_framework import serializers
from tasks.models import Comment
from users.serializers import UserMiniDetailSerializer



class CommentCreateUpdateSerializer(serializers.Serializer):
    message = serializers.CharField()

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment cannot be empty.")
        
        return value.strip()
    
    def validate(self, attrs):
        
        instance = self.instance 
        new_message = attrs.get("message")

        if instance and instance.message == new_message:
            raise serializers.ValidationError(
                "No changes detected. The new message is the same as the current one."
            )

        
        attrs["message"] = new_message
        
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        task = self.context["task"]

        return Comment.objects.create(
            organization=request.user.organization,
            task=task,
            user=request.user,
            message=validated_data["message"]
        )
    
    def update(self, instance, validated_data):
        instance.message = validated_data.get('message', instance.message)
        instance.save()
        return instance



class CommentDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    message = serializers.CharField()
    user = UserMiniDetailSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


