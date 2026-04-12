import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import Post
from .models import Like

logger = logging.getLogger(__name__)


class LikeToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        try:
            post = Post.objects.get(slug=slug, status='published')
        except Post.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            like, created = Like.objects.get_or_create(post=post, user=request.user)
            if not created:
                like.delete()
                liked = False
                logger.info("User %s unliked post %s", request.user.email, slug)
            else:
                liked = True
                logger.info("User %s liked post %s", request.user.email, slug)

            return Response({
                'liked': liked,
                'like_count': post.likes.count(),
            })
        except Exception:
            logger.exception("Error toggling like for post %s by user %s", slug, request.user.email)
            return Response({'detail': 'Action failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
