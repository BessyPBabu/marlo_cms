import logging

from django.conf import settings
from django.db import models
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts',
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    content = models.TextField()
    cover_image = models.ImageField(upload_to='posts/covers/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    read_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)

            # Safety: if title is all symbols and slugify returns empty string,
            # fall back to a pk-based slug so we never hit an infinite loop
            if not base_slug:
                logger.warning(
                    "Post title '%s' produced an empty slug — using fallback.",
                    self.title,
                )
                base_slug = f"post-{self.pk or 'new'}"

            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                if counter > 500:
                    # Hard stop to prevent runaway loop
                    logger.error("Slug uniqueness loop exceeded 500 iterations for '%s'", base_slug)
                    break

            self.slug = slug

        try:
            super().save(*args, **kwargs)
        except Exception:
            logger.exception("Failed to save post: %s", self.title)
            raise

    def increment_read_count(self):
        try:
            Post.objects.filter(pk=self.pk).update(read_count=models.F('read_count') + 1)
            self.refresh_from_db(fields=['read_count'])
        except Exception:
            logger.exception("Failed to increment read count for post %s", self.pk)

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(status='approved').count()

    @property
    def excerpt(self):
        return self.content[:200] + '...' if len(self.content) > 200 else self.content


class Attachment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='posts/attachments/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.file_name} — {self.post.title}"

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name
        try:
            super().save(*args, **kwargs)
        except Exception:
            logger.exception("Failed to save attachment for post %s", self.post_id)
            raise