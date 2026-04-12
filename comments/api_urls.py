from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.AdminCommentListAPIView.as_view(), name='api_comment_list'),
    path('post/<slug:slug>/', api_views.CommentListCreateAPIView.as_view(), name='api_comment_post'),
    path('<int:comment_id>/', api_views.CommentModerateAPIView.as_view(), name='api_comment_moderate'),
]
