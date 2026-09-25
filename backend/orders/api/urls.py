from django.urls import path

from orders.api.views import OrderDetailView, OrderListCreateView


urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
]
