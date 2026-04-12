import logging

from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from .models import Post, Attachment

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ('id', 'file', 'file_name', 'file_type', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')


class PostListSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    excerpt = serializers.CharField(read_only=True)

    class Meta:
        model = Post
        fields = (
            'id', 'title', 'slug', 'excerpt', 'cover_image',
            'author', 'status', 'read_count', 'like_count',
            'comment_count', 'published_at', 'created_at',
        )


class PostDetailSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            'id', 'title', 'slug', 'content', 'cover_image',
            'author', 'status', 'read_count', 'like_count',
            'comment_count', 'attachments', 'published_at',
            'created_at', 'updated_at',
        )


class PostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('title', 'content', 'cover_image', 'status')

    def create(self, validated_data):
        try:
            return Post.objects.create(**validated_data)
        except Exception:
            logger.exception("Failed to create post via API")
            raise
