from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.PostListAPIView.as_view(), name='api_post_list'),
    path('create/', api_views.PostCreateAPIView.as_view(), name='api_post_create'),
    path('<slug:slug>/', api_views.PostDetailAPIView.as_view(), name='api_post_detail'),
    path('<slug:slug>/update/', api_views.PostUpdateDeleteAPIView.as_view(), name='api_post_update'),
    path('<int:post_id>/attachments/', api_views.AttachmentUploadAPIView.as_view(), name='api_attachment_upload'),
    path('attachments/<int:attachment_id>/', api_views.AttachmentDeleteAPIView.as_view(), name='api_attachment_delete'),
]
