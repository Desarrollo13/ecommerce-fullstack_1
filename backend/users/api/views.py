from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema

from users.api.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from users.notifications import send_password_reset_email, send_welcome_email


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        send_welcome_email(user)


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            base_url = settings.FRONTEND_URL or request.build_absolute_uri("/").rstrip("/")
            reset_url = f"{base_url}/password-reset?uid={uid}&token={token}"
            send_password_reset_email(user, reset_url)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = get_user_model().objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return Response({"detail": "El enlace de restablecimiento no es válido."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "El enlace de restablecimiento no es válido o venció."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=("password",))
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    @extend_schema(operation_id="auth_logout", request=None, responses={204: None})
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("ecommerce-refresh-token", path="/api/auth/")
        return response
