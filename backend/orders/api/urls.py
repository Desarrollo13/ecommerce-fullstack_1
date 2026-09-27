from django.urls import path

from orders.api.views import (
    OrderDetailView,
    OrderListCreateView,
    PaymentPreferenceView,
    MercadoPagoWebhookView,
    OrderStatusUpdateView,
    PaymentStatusUpdateView,
)


urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("payments/webhook/", MercadoPagoWebhookView.as_view(), name="mercadopago-webhook"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path(
        "<int:pk>/payment-preference/",
        PaymentPreferenceView.as_view(),
        name="order-payment-preference",
    ),
    path("<int:pk>/status/", OrderStatusUpdateView.as_view(), name="order-status"),
    path(
        "<int:pk>/payment-status/",
        PaymentStatusUpdateView.as_view(),
        name="order-payment-status",
    ),
]
