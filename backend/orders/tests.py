from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cart.models import Cart, CartItem
from orders.models import Order
from products.models import Category, Product


class OrderApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ana", email="ana@example.com", password="secure-password"
        )
        self.other_user = get_user_model().objects.create_user(
            username="bea", email="bea@example.com", password="secure-password"
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

    def test_order_creation_requires_authentication(self):
        response = self.client.post("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_creates_order_snapshots_and_reduces_stock(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.client.force_authenticate(self.user)

        response = self.client.post("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Order.Status.PENDING)
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

        response = self.client.post("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_user_cannot_read_another_users_order(self):
        order = Order.objects.create(user=self.user, total="100.00")
        self.client.force_authenticate(self.other_user)

        response = self.client.get(f"/api/orders/{order.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
