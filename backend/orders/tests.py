import hashlib
import hmac

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from products.models import Category, Product


class OrderApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ana", email="ana@example.com", password="secure-password"
        )
        self.other_user = get_user_model().objects.create_user(
            username="bea", email="bea@example.com", password="secure-password"
        )
        self.staff = get_user_model().objects.create_user(
            username="staff",
            email="staff@example.com",
            password="secure-password",
            is_staff=True,
        )
        category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Headphones",
            description="Wireless headphones",
            price="100.00",
            stock=5,
            category=category,
        )
        self.cart = Cart.objects.create(user=self.user)

    def checkout_data(self):
        return {
            "shipping_address": "Av. San Martin 123, Mendoza, Argentina",
            "payment_method": Order.PaymentMethod.CARD,
        }

    def test_order_creation_requires_authentication(self):
        response = self.client.post("/api/orders/", self.checkout_data())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_creates_order_snapshots_and_reduces_stock(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.client.force_authenticate(self.user)

        response = self.client.post("/api/orders/", self.checkout_data())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Order.Status.PENDING)
        self.assertEqual(response.data["payment_status"], Order.PaymentStatus.PENDING)
        self.assertEqual(response.data["shipping_address"], self.checkout_data()["shipping_address"])
        self.assertEqual(response.data["payment_method"], Order.PaymentMethod.CARD)
        self.assertEqual(response.data["total"], "200.00")
        self.assertEqual(response.data["items"][0]["product_name"], "Headphones")
        self.assertEqual(response.data["items"][0]["unit_price"], "100.00")
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_checkout_keeps_cart_when_stock_changed(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=3)
        self.product.stock = 2
        self.product.save(update_fields=("stock",))
        self.client.force_authenticate(self.user)

        response = self.client.post("/api/orders/", self.checkout_data())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_checkout_requires_shipping_address_and_payment_method(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)

        response = self.client.post("/api/orders/", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shipping_address", response.data)
        self.assertIn("payment_method", response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_user_cannot_read_another_users_order(self):
        order = Order.objects.create(user=self.user, total="100.00")
        self.client.force_authenticate(self.other_user)

        response = self.client.get(f"/api/orders/{order.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(
        MERCADOPAGO_ACCESS_TOKEN="TEST-access-token",
        MERCADOPAGO_WEBHOOK_URL="https://example.test/api/orders/payments/webhook/",
    )
    @patch("orders.api.views.mercadopago.SDK")
    def test_user_can_create_a_mercadopago_payment_preference(self, mock_sdk):
        order = self.create_order_with_item()
        mock_sdk.return_value.preference.return_value.create.return_value = {
            "status": 201,
            "response": {
                "id": "preference-123",
                "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=preference-123",
            },
        }
        self.client.force_authenticate(self.user)

        response = self.client.post(f"/api/orders/{order.pk}/payment-preference/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["preference_id"], "preference-123")
        self.assertEqual(
            response.data["init_point"],
            "https://www.mercadopago.com/checkout/v1/redirect?pref_id=preference-123",
        )
        mock_sdk.assert_called_once_with("TEST-access-token")
        mock_sdk.return_value.preference.return_value.create.assert_called_once()
        preference_data = mock_sdk.return_value.preference.return_value.create.call_args.args[0]
        self.assertEqual(
            preference_data["notification_url"],
            "https://example.test/api/orders/payments/webhook/",
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_provider, Order.PaymentProvider.MERCADO_PAGO)
        self.assertEqual(order.provider_preference_id, "preference-123")

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="")
    def test_payment_preference_requires_mercadopago_configuration(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.user)

        response = self.client.post(f"/api/orders/{order.pk}/payment-preference/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_paid_order_cannot_create_another_payment_preference(self):
        order = self.create_order_with_item()
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=("payment_status",))
        self.client.force_authenticate(self.user)

        response = self.client.post(f"/api/orders/{order.pk}/payment-preference/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        MERCADOPAGO_ACCESS_TOKEN="TEST-access-token",
        MERCADOPAGO_WEBHOOK_SECRET="webhook-secret",
    )
    @patch("orders.api.views.mercadopago.SDK")
    def test_mercadopago_webhook_marks_an_approved_payment_as_paid(self, mock_sdk):
        order = self.create_order_with_item()
        order.payment_provider = Order.PaymentProvider.MERCADO_PAGO
        order.save(update_fields=("payment_provider",))
        mock_sdk.return_value.payment.return_value.get.return_value = {
            "status": 200,
            "response": {
                "external_reference": str(order.pk),
                "transaction_amount": "200.00",
                "status": "approved",
            },
        }
        timestamp = "1234567890"
        request_id = "request-123"
        manifest = f"id:payment-123;request-id:{request_id};ts:{timestamp};"
        signature = hmac.new(
            b"webhook-secret", manifest.encode(), hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/api/orders/payments/webhook/",
            {"type": "payment", "data": {"id": "payment-123"}},
            format="json",
            headers={
                "X-Signature": f"ts={timestamp},v1={signature}",
                "X-Request-Id": request_id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.provider_payment_id, "payment-123")

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="TEST-access-token")
    @patch("orders.api.views.mercadopago.SDK")
    def test_legacy_payment_notification_marks_an_approved_payment_as_paid(self, mock_sdk):
        order = self.create_order_with_item()
        order.payment_provider = Order.PaymentProvider.MERCADO_PAGO
        order.save(update_fields=("payment_provider",))
        mock_sdk.return_value.payment.return_value.get.return_value = {
            "status": 200,
            "response": {
                "external_reference": str(order.pk),
                "transaction_amount": "200.00",
                "status": "approved",
            },
        }

        response = self.client.post(
            "/api/orders/payments/webhook/?id=payment-123&topic=payment",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.provider_payment_id, "payment-123")

    @override_settings(MERCADOPAGO_WEBHOOK_SECRET="webhook-secret")
    def test_mercadopago_webhook_rejects_invalid_signatures(self):
        response = self.client.post(
            "/api/orders/payments/webhook/",
            {"type": "payment", "data": {"id": "payment-123"}},
            format="json",
            headers={"X-Signature": "ts=1234567890,v1=invalid"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(
        MERCADOPAGO_ACCESS_TOKEN="TEST-access-token",
        MERCADOPAGO_WEBHOOK_SECRET="webhook-secret",
    )
    @patch("orders.api.views.mercadopago.SDK")
    def test_mercadopago_webhook_ignores_unknown_payments(self, mock_sdk):
        mock_sdk.return_value.payment.return_value.get.return_value = {
            "status": 200,
            "response": {"external_reference": "unknown", "transaction_amount": "200.00"},
        }
        timestamp = "1234567890"
        request_id = "request-123"
        manifest = f"id:payment-123;request-id:{request_id};ts:{timestamp};"
        signature = hmac.new(
            b"webhook-secret", manifest.encode(), hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/api/orders/payments/webhook/",
            {"type": "payment", "data": {"id": "payment-123"}},
            format="json",
            headers={
                "X-Signature": f"ts={timestamp},v1={signature}",
                "X-Request-Id": request_id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @override_settings(
        MERCADOPAGO_ACCESS_TOKEN="TEST-access-token",
        MERCADOPAGO_WEBHOOK_SECRET="webhook-secret",
    )
    @patch("orders.api.views.mercadopago.SDK")
    def test_mercadopago_webhook_ignores_missing_provider_payments(self, mock_sdk):
        mock_sdk.return_value.payment.return_value.get.return_value = {"status": 404}
        timestamp = "1234567890"
        request_id = "request-123"
        manifest = f"id:payment-123;request-id:{request_id};ts:{timestamp};"
        signature = hmac.new(
            b"webhook-secret", manifest.encode(), hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/api/orders/payments/webhook/",
            {"type": "payment", "data": {"id": "payment-123"}},
            format="json",
            headers={
                "X-Signature": f"ts={timestamp},v1={signature}",
                "X-Request-Id": request_id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_database_rejects_invalid_order_amounts_and_quantities(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(user=self.user, total="-1.00")

        order = Order.objects.create(user=self.user, total="0.00")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderItem.objects.create(
                    order=order,
                    product=self.product,
                    product_name=self.product.name,
                    unit_price="10.00",
                    quantity=0,
                    line_total="0.00",
                )

    def create_order_with_item(self, status=Order.Status.PENDING):
        self.product.stock = 3
        self.product.save(update_fields=("stock",))
        order = Order.objects.create(user=self.user, status=status, total="200.00")
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price="100.00",
            quantity=2,
            line_total="200.00",
        )
        return order

    def test_staff_can_progress_an_order_through_valid_statuses(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.staff)

        response = self.client.patch(
            f"/api/orders/{order.pk}/status/", {"status": Order.Status.PROCESSING}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            f"/api/orders/{order.pk}/payment-status/",
            {"payment_status": Order.PaymentStatus.PAID},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], Order.PaymentStatus.PAID)

        for new_status in (
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        ):
            response = self.client.patch(
                f"/api/orders/{order.pk}/status/", {"status": new_status}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], new_status)

    def test_status_update_requires_staff(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            f"/api/orders/{order.pk}/status/", {"status": Order.Status.PROCESSING}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_payment_status_update_requires_staff(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            f"/api/orders/{order.pk}/payment-status/",
            {"payment_status": Order.PaymentStatus.PAID},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_payment_status_transition_is_rejected(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.staff)

        response = self.client.patch(
            f"/api/orders/{order.pk}/payment-status/",
            {"payment_status": Order.PaymentStatus.REFUNDED},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    def test_invalid_order_transition_is_rejected(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.staff)

        response = self.client.patch(
            f"/api/orders/{order.pk}/status/", {"status": Order.Status.SHIPPED}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_cancelling_an_order_restores_stock(self):
        order = self.create_order_with_item()
        self.client.force_authenticate(self.staff)

        response = self.client.patch(
            f"/api/orders/{order.pk}/status/", {"status": Order.Status.CANCELLED}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Order.Status.CANCELLED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_shipped_orders_cannot_be_cancelled(self):
        order = self.create_order_with_item(status=Order.Status.SHIPPED)
        self.client.force_authenticate(self.staff)

        response = self.client.patch(
            f"/api/orders/{order.pk}/status/", {"status": Order.Status.CANCELLED}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
