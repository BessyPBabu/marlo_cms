import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import UserDetailSerializer, UserPublicSerializer, RegisterSerializer

logger = logging.getLogger(__name__)


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Registration validation failed: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserPublicSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Unexpected error during API registration")
            return Response(
                {'detail': 'Registration failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]


class UserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'detail': 'Cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            logger.info("Admin deleted user via API: %s", user.email)
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("Error deleting user %s via API", user.pk)
            return Response({'detail': 'Delete failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
