from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    path('register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', api_views.MeAPIView.as_view(), name='api_me'),
    path('users/', api_views.UserListAPIView.as_view(), name='api_user_list'),
    path('users/<int:pk>/', api_views.UserDetailAPIView.as_view(), name='api_user_detail'),
]
