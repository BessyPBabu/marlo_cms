from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Admin user management
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('dashboard/users/', views.user_list, name='dashboard_user_list'),
    path('dashboard/users/create/', views.user_create, name='dashboard_user_create'),
    path('dashboard/users/<int:user_id>/edit/', views.user_edit, name='dashboard_user_edit'),
    path('dashboard/users/<int:user_id>/delete/', views.user_delete, name='dashboard_user_delete'),
]
