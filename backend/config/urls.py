from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('products.api.urls')),
    path("api/auth/", include("users.api.urls")),
    path("api/cart/", include("cart.api.urls")),
    path("api/orders/", include("orders.api.urls")),
    path("", TemplateView.as_view(template_name="index.html")),
    path("payment-result", TemplateView.as_view(template_name="index.html")),
]
