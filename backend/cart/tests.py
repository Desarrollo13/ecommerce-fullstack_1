from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cart.api.views import get_cart
from cart.models import Cart, CartItem
from products.models import Category, Product


class CartApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ana", email="ana@example.com", password="secure-password"
        )
        category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Headphones",
            description="Wireless headphones",
            price="100.00",
            stock=5,
            category=category,
        )

    def test_cart_requires_authentication(self):
        response = self.client.get("/api/cart/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_adds_and_increments_an_item(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/cart/items/", {"product_id": self.product.pk, "quantity": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            "/api/cart/items/", {"product_id": self.product.pk, "quantity": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], 3)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_cart_rejects_quantity_above_stock(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/cart/items/", {"product_id": self.product.pk, "quantity": 6}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_cart_item_can_be_updated_and_deleted(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/cart/items/", {"product_id": self.product.pk, "quantity": 1}
        )

        response = self.client.patch(
            f"/api/cart/items/{response.data['id']}/", {"quantity": 4}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantity"], 4)

        response = self.client.delete(f"/api/cart/items/{response.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.exists())

    def test_cart_does_not_update_an_inactive_product(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/cart/items/", {"product_id": self.product.pk, "quantity": 1}
        )
        self.product.is_active = False
        self.product.save(update_fields=("is_active",))

        response = self.client.patch(
            f"/api/cart/items/{response.data['id']}/", {"quantity": 2}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "This product is no longer available.")
        self.assertEqual(CartItem.objects.get().quantity, 1)

    def test_get_cart_reuses_a_single_cart_for_the_user(self):
        first_cart = get_cart(self.user)
        second_cart = get_cart(self.user)

        self.assertEqual(first_cart.pk, second_cart.pk)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)
