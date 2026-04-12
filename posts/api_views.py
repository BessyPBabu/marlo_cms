import logging

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Post, Attachment
from .serializers import PostListSerializer, PostDetailSerializer, PostWriteSerializer, AttachmentSerializer

logger = logging.getLogger(__name__)


class PostListAPIView(generics.ListAPIView):
    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Post.objects.select_related('author')
        # Admins can see all posts; others see only published
        if self.request.user.is_staff:
            return qs
        return qs.filter(status='published')


class PostDetailAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        try:
            post = Post.objects.select_related('author').prefetch_related(
                'attachments', 'likes', 'comments'
            ).get(slug=slug, status='published')
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error fetching post %s", slug)
            return Response({'detail': 'Server error.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Increment read count
        post.increment_read_count()
        serializer = PostDetailSerializer(post, context={'request': request})
        return Response(serializer.data)


class PostCreateAPIView(generics.CreateAPIView):
    serializer_class = PostWriteSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        try:
            post = serializer.save(author=self.request.user)
            if post.status == 'published':
                Post.objects.filter(pk=post.pk).update(published_at=timezone.now())
            logger.info("Post created via API: %s by %s", post.title, self.request.user.email)
        except Exception:
            logger.exception("API post create failed")
            raise


class PostUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    lookup_field = 'slug'
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PostDetailSerializer
        return PostWriteSerializer

    def perform_destroy(self, instance):
        try:
            logger.info("Post deleted via API: %s", instance.title)
            instance.delete()
        except Exception:
            logger.exception("API post delete failed: %s", instance.pk)
            raise


class AttachmentUploadAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > 20 * 1024 * 1024:
            return Response({'detail': 'File exceeds 20 MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attachment = Attachment.objects.create(
                post=post,
                file=file,
                file_name=file.name,
                file_type=file.content_type,
            )
            logger.info("Attachment uploaded for post %s: %s", post_id, file.name)
            return Response(AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Attachment upload failed for post %s", post_id)
            return Response({'detail': 'Upload failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AttachmentDeleteAPIView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, attachment_id):
        try:
            attachment = Attachment.objects.get(pk=attachment_id)
            attachment.delete()
            logger.info("Attachment deleted: %s", attachment_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Attachment.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Attachment delete failed: %s", attachment_id)
            return Response({'detail': 'Delete failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
