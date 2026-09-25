from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase


class UserModelTests(TestCase):
    def test_registration_creates_a_customer_without_returning_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "ana",
                "email": "ana@example.com",
                "password": "secure-password",
                "first_name": "Ana",
                "last_name": "Perez",
                "phone": "2615551234",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        user = get_user_model().objects.get(email="ana@example.com")
        self.assertTrue(user.check_password("secure-password"))
        self.assertEqual(user.role, get_user_model().Role.CUSTOMER)

    def test_registration_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="secure-password",
        )

        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "ana2",
                "email": "ana@example.com",
                "password": "another-secure-password",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_email_is_the_login_identifier(self):
        user = get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="secure-password",
        )

        self.assertEqual(get_user_model().USERNAME_FIELD, "email")
        self.assertEqual(user.role, get_user_model().Role.CUSTOMER)

    def test_email_must_be_unique(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="secure-password",
        )

        with self.assertRaises(IntegrityError):
            user_model.objects.create_user(
                username="ana2",
                email="ana@example.com",
                password="secure-password",
            )

    def test_jwt_login_accepts_email(self):
        get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="secure-password",
        )

        response = self.client.post(
            "/api/auth/token/",
            {"email": "ana@example.com", "password": "secure-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
