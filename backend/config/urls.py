from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('products.api.urls')),
    path("api/auth/", include("users.api.urls")),
    path("api/cart/", include("cart.api.urls")),
    path("api/orders/", include("orders.api.urls")),
    
    # jwt
    path("api/auth/token/", TokenObtainPairView.as_view()),
    path("api/auth/token/refresh/", TokenRefreshView.as_view()),        
]
