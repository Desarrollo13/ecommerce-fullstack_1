from django.core.management.base import BaseCommand
from django.db import transaction

from orders.services import expire_payment_reservations


class Command(BaseCommand):
    help = "Cancels expired online payment reservations and restores their stock."

    def handle(self, *args, **options):
        with transaction.atomic():
            expired_count = expire_payment_reservations()
        self.stdout.write(
            self.style.SUCCESS(f"Expired {expired_count} payment reservation(s).")
        )
