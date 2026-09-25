from django.urls import path

from cart.api.views import CartItemCreateView, CartItemDetailView, CartView


urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemCreateView.as_view(), name="cart-item-create"),
    path("items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
]
