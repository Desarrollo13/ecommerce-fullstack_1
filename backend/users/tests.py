import os

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch


class UserModelTests(TestCase):
    @patch("users.api.views.send_welcome_email")
    def test_registration_creates_a_customer_without_returning_password(
        self, mock_send_welcome_email
    ):
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
        mock_send_welcome_email.assert_called_once_with(user)

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
        self.assertNotIn("refresh", response.data)
        self.assertIn("ecommerce-refresh-token", response.cookies)
        self.assertTrue(response.cookies["ecommerce-refresh-token"]["httponly"])

    def test_jwt_refresh_uses_the_http_only_cookie(self):
        get_user_model().objects.create_user(
            username="ana",
            email="ana@example.com",
            password="secure-password",
        )
        login_response = self.client.post(
            "/api/auth/token/",
            {"email": "ana@example.com", "password": "secure-password"},
        )
        self.client.cookies["ecommerce-refresh-token"] = login_response.cookies[
            "ecommerce-refresh-token"
        ].value

        response = self.client.post("/api/auth/token/refresh/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_logout_clears_the_refresh_cookie(self):
        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies["ecommerce-refresh-token"]["max-age"], 0)

    def test_openapi_documentation_is_public(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
        self.assertEqual(self.client.get("/api/redoc/").status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_URL="https://store.example")
    def test_password_reset_sends_a_one_time_link_and_updates_the_password(self):
        user = get_user_model().objects.create_user(
            username="ana", email="ana@example.com", password="old-password"
        )

        response = self.client.post("/api/auth/password-reset/", {"email": user.email})

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        self.assertIn(f"https://store.example/password-reset?uid={uid}&token=", mail.outbox[0].body)

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "password": "new-secure-password"},
        )

        self.assertEqual(response.status_code, 204)
        user.refresh_from_db()
        self.assertTrue(user.check_password("new-secure-password"))
        reused_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "password": "another-password"},
        )
        self.assertEqual(reused_response.status_code, 400)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_does_not_disclose_unknown_emails(self):
        response = self.client.post("/api/auth/password-reset/", {"email": "missing@example.com"})

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(mail.outbox), 0)

    def test_ensure_admin_creates_and_updates_the_configured_user(self):
        with patch.dict(
            os.environ,
            {
                "DJANGO_ADMIN_EMAIL": "admin@example.com",
                "DJANGO_ADMIN_PASSWORD": "initial-admin-password",
                "DJANGO_ADMIN_USERNAME": "store-admin",
            },
            clear=False,
        ):
            call_command("ensure_admin")

            admin = get_user_model().objects.get(email="admin@example.com")
            self.assertTrue(admin.is_staff)
            self.assertTrue(admin.is_superuser)
            self.assertEqual(admin.role, get_user_model().Role.ADMIN)
            self.assertTrue(admin.check_password("initial-admin-password"))

            os.environ["DJANGO_ADMIN_PASSWORD"] = "updated-admin-password"
            call_command("ensure_admin")

        admin.refresh_from_db()
        self.assertTrue(admin.check_password("updated-admin-password"))
