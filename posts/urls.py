from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.post_list, name='post_list'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('about/', views.about, name='about'),

    # Admin dashboard — posts
    path('dashboard/posts/', views.dashboard_post_list, name='dashboard_post_list'),
    path('dashboard/posts/create/', views.dashboard_post_create, name='dashboard_post_create'),
    path('dashboard/posts/<int:post_id>/edit/', views.dashboard_post_edit, name='dashboard_post_edit'),
    path('dashboard/posts/<int:post_id>/delete/', views.dashboard_post_delete, name='dashboard_post_delete'),
    path('dashboard/attachments/<int:attachment_id>/delete/', views.dashboard_attachment_delete, name='dashboard_attachment_delete'),
]
