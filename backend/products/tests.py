from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Category, Product


class ProductApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff",
            email="staff@example.com",
            password="secure-password",
            is_staff=True,
        )
        self.active_category = Category.objects.create(name="Active")
        self.inactive_category = Category.objects.create(
            name="Inactive", is_active=False
        )
        self.public_product = Product.objects.create(
            name="Public product",
            description="Visible to everyone",
            price="100.00",
            stock=3,
            category=self.active_category,
        )
        self.inactive_product = Product.objects.create(
            name="Inactive product",
            description="Hidden product",
            price="100.00",
            stock=2,
            is_active=False,
            category=self.active_category,
        )
        self.product_in_inactive_category = Product.objects.create(
            name="Hidden category product",
            description="Hidden by category",
            price="100.00",
            stock=1,
            category=self.inactive_category,
        )

    def test_public_catalog_only_exposes_active_products_without_stock(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([product["id"] for product in response.data], [self.public_product.id])
        self.assertNotIn("stock", response.data[0])
        self.assertNotIn("is_active", response.data[0])

    def test_public_catalog_hides_inactive_product_details(self):
        response = self.client.get(f"/api/products/{self.inactive_product.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_catalog_only_exposes_active_categories_without_status(self):
        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([category["id"] for category in response.data], [self.active_category.id])
        self.assertNotIn("is_active", response.data[0])

    def test_staff_catalog_includes_inactive_products_and_stock(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertIn("stock", response.data[0])
        self.assertIn("is_active", response.data[0])

    def test_product_creation_requires_staff(self):
        payload = {
            "name": "New product",
            "description": "Created by staff",
            "price": "50.00",
            "stock": 2,
            "category": self.active_category.id,
        }

        response = self.client.post("/api/products/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.staff)
        response = self.client.post("/api/products/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
