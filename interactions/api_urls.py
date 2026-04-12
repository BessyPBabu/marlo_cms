from django.urls import path
from . import api_views

urlpatterns = [
    path('like/<slug:slug>/', api_views.LikeToggleAPIView.as_view(), name='api_like_toggle'),
]
