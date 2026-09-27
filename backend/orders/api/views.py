import hashlib
import hmac
from decimal import Decimal, InvalidOperation

import mercadopago

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from orders.api.serializers import (
    CheckoutSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    PaymentStatusSerializer,
)
from orders.models import Order, OrderItem
from products.models import Product


def is_valid_mercadopago_signature(request, data_id):
    if not settings.MERCADOPAGO_WEBHOOK_SECRET:
        return False

    signature = request.headers.get("x-signature", "")
    values = dict(
        value.split("=", 1)
        for value in signature.split(",")
        if "=" in value
    )
    timestamp = values.get("ts")
    received_hash = values.get("v1")
    if not timestamp or not received_hash:
        return False

    manifest = (
        f"id:{data_id};request-id:{request.headers.get('x-request-id', '')};ts:{timestamp};"
    )
    expected_hash = hmac.new(
        settings.MERCADOPAGO_WEBHOOK_SECRET.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()
    return constant_time_compare(expected_hash, received_hash)


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                cart = Cart.objects.select_for_update().get(user=request.user)
            except Cart.DoesNotExist:
                return Response(
                    {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
                )

            cart_items = list(
                CartItem.objects.select_for_update()
                .filter(cart=cart)
                .order_by("product_id")
            )
            if not cart_items:
                return Response(
                    {"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
                )

            products = {
                product.pk: product
                for product in Product.objects.select_for_update()
                .filter(pk__in=[item.product_id for item in cart_items])
                .order_by("pk")
            }

            for item in cart_items:
                product = products.get(item.product_id)
                if product is None or not product.is_active:
                    return Response(
                        {"detail": "A cart product is no longer available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if item.quantity > product.stock:
                    return Response(
                        {"detail": "A cart product no longer has enough stock."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            total = sum(
                (
                    products[item.product_id].price * item.quantity
                    for item in cart_items
                ),
                Decimal("0.00"),
            )
            order = Order.objects.create(
                user=request.user,
                shipping_address=serializer.validated_data["shipping_address"],
                payment_method=serializer.validated_data["payment_method"],
                total=total,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=products[item.product_id],
                        product_name=products[item.product_id].name,
                        unit_price=products[item.product_id].price,
                        quantity=item.quantity,
                        line_total=products[item.product_id].price * item.quantity,
                    )
                    for item in cart_items
                ]
            )

            for item in cart_items:
                product = products[item.product_id]
                product.stock -= item.quantity
                product.save(update_fields=("stock", "updated_at"))

            CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"), pk=pk, user=request.user
        )
        return Response(OrderSerializer(order).data)


class PaymentPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)
        if order.status == Order.Status.CANCELLED:
            return Response(
                {"detail": "Cancelled orders cannot be paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.payment_status != Order.PaymentStatus.PENDING:
            return Response(
                {"detail": "This order is no longer awaiting payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.payment_method == Order.PaymentMethod.CASH_ON_DELIVERY:
            return Response(
                {"detail": "Cash on delivery orders do not require an online payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            return Response(
                {"detail": "Mercado Pago is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        preference_data = {
            "items": [
                {
                    "id": str(item.product_id or item.pk),
                    "title": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "currency_id": "ARS",
                }
                for item in order.items.all()
            ],
            "external_reference": str(order.pk),
            "metadata": {"order_id": order.pk},
        }
        if settings.MERCADOPAGO_WEBHOOK_URL:
            preference_data["notification_url"] = settings.MERCADOPAGO_WEBHOOK_URL
        if settings.FRONTEND_URL:
            result_url = f"{settings.FRONTEND_URL}/payment-result"
            preference_data["back_urls"] = {
                "success": result_url,
                "pending": result_url,
                "failure": result_url,
            }
            preference_data["auto_return"] = "approved"
        result = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN).preference().create(
            preference_data
        )
        preference = result.get("response", {})
        if result.get("status") not in (200, 201) or not preference.get("id"):
            return Response(
                {"detail": "Could not create the Mercado Pago payment preference."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        order.payment_provider = Order.PaymentProvider.MERCADO_PAGO
        order.provider_preference_id = preference["id"]
        order.save(
            update_fields=(
                "payment_provider",
                "provider_preference_id",
                "updated_at",
            )
        )
        return Response(
            {
                "preference_id": preference["id"],
                "init_point": preference.get("init_point"),
                "sandbox_init_point": preference.get("sandbox_init_point"),
            },
            status=status.HTTP_201_CREATED,
        )


class MercadoPagoWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data_id = str(
            request.data.get("data", {}).get("id")
            or request.query_params.get("data.id")
            or request.query_params.get("id", "")
        )
        notification_type = (
            request.data.get("type")
            or request.query_params.get("type")
            or request.query_params.get("topic")
        )
        if notification_type != "payment" or not data_id:
            return Response(status=status.HTTP_204_NO_CONTENT)
        is_legacy_ipn = request.query_params.get("topic") == "payment"
        if not is_legacy_ipn and not is_valid_mercadopago_signature(request, data_id):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        result = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN).payment().get(data_id)
        payment = result.get("response", {})
        if result.get("status") == 404:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if result.get("status") != 200 or not payment:
            return Response(status=status.HTTP_502_BAD_GATEWAY)

        try:
            order_id = int(payment.get("external_reference", ""))
            transaction_amount = Decimal(str(payment["transaction_amount"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            return Response(status=status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            order = Order.objects.select_for_update().filter(
                pk=order_id,
                payment_provider=Order.PaymentProvider.MERCADO_PAGO,
            ).first()
            if order is None or order.status == Order.Status.CANCELLED:
                return Response(status=status.HTTP_204_NO_CONTENT)
            if transaction_amount != order.total:
                return Response(status=status.HTTP_204_NO_CONTENT)

            payment_statuses = {
                "approved": Order.PaymentStatus.PAID,
                "rejected": Order.PaymentStatus.FAILED,
                "cancelled": Order.PaymentStatus.FAILED,
                "refunded": Order.PaymentStatus.REFUNDED,
                "charged_back": Order.PaymentStatus.REFUNDED,
            }
            new_status = payment_statuses.get(payment.get("status"))
            if new_status is None:
                return Response(status=status.HTTP_204_NO_CONTENT)
            if new_status != order.payment_status and not order.can_transition_payment_to(new_status):
                return Response(status=status.HTTP_204_NO_CONTENT)

            order.payment_status = new_status
            order.provider_payment_id = data_id
            order.save(update_fields=("payment_status", "provider_payment_id", "updated_at"))

        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderStatusUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
            if not order.can_transition_to(new_status):
                return Response(
                    {"detail": "This order status transition is not allowed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                new_status == Order.Status.PROCESSING
                and order.payment_status != Order.PaymentStatus.PAID
            ):
                return Response(
                    {"detail": "The order must be paid before processing."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_status == Order.Status.CANCELLED:
                items = list(order.items.select_for_update())
                products = {
                    product.pk: product
                    for product in Product.objects.select_for_update().filter(
                        pk__in=[item.product_id for item in items if item.product_id]
                    )
                }
                for item in items:
                    product = products.get(item.product_id)
                    if product is not None:
                        product.stock += item.quantity
                        product.save(update_fields=("stock", "updated_at"))

            order.status = new_status
            order.save(update_fields=("status", "updated_at"))

        return Response(OrderSerializer(order).data)


class PaymentStatusUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["payment_status"]

        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
            if not order.can_transition_payment_to(new_status):
                return Response(
                    {"detail": "This payment status transition is not allowed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.payment_status = new_status
            order.save(update_fields=("payment_status", "updated_at"))

        return Response(OrderSerializer(order).data)
