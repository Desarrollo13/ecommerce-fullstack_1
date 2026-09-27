from django.urls import path

from users.api.views import (
    RegisterView,
    SessionLoginView,
    SessionLogoutView,
    SessionRefreshView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", SessionLoginView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", SessionRefreshView.as_view(), name="token-refresh"),
    path("logout/", SessionLogoutView.as_view(), name="logout"),
]
