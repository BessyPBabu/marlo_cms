"""
URL configuration for marlo_cms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import logging

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

logger = logging.getLogger(__name__)

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # Template views
    path('', include('posts.urls')),
    path('', include('accounts.urls')),
    path('', include('comments.urls')),

    # REST API
    path('api/auth/', include('accounts.api_urls')),
    path('api/posts/', include('posts.api_urls')),
    path('api/comments/', include('comments.api_urls')),
    path('api/interactions/', include('interactions.api_urls')),
]

# In production, Cloudinary serves media — this is only for local dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

