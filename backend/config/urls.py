from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('products.api.urls')),
    path("api/auth/", include("users.api.urls")),
    path("api/cart/", include("cart.api.urls")),
    path("api/orders/", include("orders.api.urls")),
]
