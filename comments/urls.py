from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/comments/', views.dashboard_comment_list, name='dashboard_comment_list'),
    path('dashboard/comments/<int:comment_id>/moderate/', views.dashboard_comment_moderate, name='dashboard_comment_moderate'),
    path('dashboard/comments/<int:comment_id>/delete/', views.dashboard_comment_delete, name='dashboard_comment_delete'),
]
