import os

from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    help = "Creates or updates the administrator configured through environment variables."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("DJANGO_ADMIN_PASSWORD", "")
        username = os.getenv("DJANGO_ADMIN_USERNAME", "admin").strip()
        if not email or not password:
            raise CommandError(
                "DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD must be configured."
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "is_staff": True,
                "is_superuser": True,
                "role": User.Role.ADMIN,
            },
        )
        user.username = username
        user.is_staff = True
        user.is_superuser = True
        user.role = User.Role.ADMIN
        user.set_password(password)
        user.save()
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} administrator {email}."))
