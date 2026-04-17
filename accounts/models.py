import logging

from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger(__name__)


class CustomUser(AbstractUser):
    # ROLE_GUEST = 'guest'
    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        # (ROLE_GUEST, 'Guest'),
        (ROLE_USER, 'User'),
        (ROLE_ADMIN, 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Use email as the login identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN or self.is_staff

    def save(self, *args, **kwargs):
        # Sync role field with is_staff for consistency
        if self.is_staff:
            self.role = self.ROLE_ADMIN
        try:
            super().save(*args, **kwargs)
        except Exception:
            logger.exception("Failed to save user %s", self.email)
            raise
