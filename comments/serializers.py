import logging

from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .models import Comment

logger = logging.getLogger(__name__)


class CommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'user', 'body', 'status', 'created_at')
        read_only_fields = ('id', 'user', 'status', 'created_at')

    def validate_body(self, value):
        stripped = value.strip()
        if len(stripped) < 2:
            raise serializers.ValidationError("Comment is too short.")
        if len(stripped) > 2000:
            raise serializers.ValidationError("Comment cannot exceed 2000 characters.")
        return stripped

    def create(self, validated_data):
        try:
            return Comment.objects.create(**validated_data)
        except Exception:
            logger.exception("Failed to create comment via API")
            raise


class CommentModerateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'status')
