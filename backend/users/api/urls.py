from django.urls import path

from users.api.views import (
    RegisterView,
    SessionLoginView,
    SessionLogoutView,
    SessionRefreshView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", SessionLoginView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", SessionRefreshView.as_view(), name="token-refresh"),
    path("logout/", SessionLogoutView.as_view(), name="logout"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]
