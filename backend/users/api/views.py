from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.api.serializers import RegisterSerializer
from users.notifications import send_welcome_email


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        send_welcome_email(user)


def set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        "ecommerce-refresh-token",
        refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/auth/",
    )


class SessionLoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh_token = response.data.pop("refresh")
        set_refresh_cookie(response, refresh_token)
        return response


class SessionRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data={"refresh": request.COOKIES.get("ecommerce-refresh-token", "")}
        )
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        if refresh_token := response.data.pop("refresh", None):
            set_refresh_cookie(response, refresh_token)
        return response


class SessionLogoutView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("ecommerce-refresh-token", path="/api/auth/")
        return response
