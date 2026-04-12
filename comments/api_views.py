import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import Post
from .models import Comment
from .serializers import CommentSerializer, CommentModerateSerializer

logger = logging.getLogger(__name__)


class CommentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        try:
            post = Post.objects.get(slug=slug, status='published')
        except Post.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        comments = post.comments.filter(status='approved').select_related('user')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, slug):
        try:
            post = Post.objects.get(slug=slug, status='published')
        except Post.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CommentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            comment = serializer.save(post=post, user=request.user)
            logger.info("Comment submitted by %s on post %s", request.user.email, slug)
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Error saving comment")
            return Response({'detail': 'Could not save comment.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentModerateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, comment_id):
        try:
            comment = Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CommentModerateSerializer(comment, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            logger.info("Comment %s moderated to status=%s by %s",
                        comment_id, comment.status, request.user.email)
            return Response(serializer.data)
        except Exception:
            logger.exception("Error moderating comment %s", comment_id)
            return Response({'detail': 'Moderation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(pk=comment_id)
            comment.delete()
            logger.info("Comment %s deleted by admin %s", comment_id, request.user.email)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comment.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error deleting comment %s", comment_id)
            return Response({'detail': 'Delete failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminCommentListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        filter_status = request.query_params.get('status', 'pending')
        valid_statuses = ['pending', 'approved', 'blocked', 'all']
        if filter_status not in valid_statuses:
            filter_status = 'pending'

        try:
            qs = Comment.objects.select_related('user', 'post')
            if filter_status != 'all':
                qs = qs.filter(status=filter_status)
            serializer = CommentSerializer(qs, many=True)
            return Response(serializer.data)
        except Exception:
            logger.exception("Error fetching admin comment list")
            return Response({'detail': 'Server error.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
