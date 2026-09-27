from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from orders.models import Order
from products.models import Product


PAYMENT_RESERVATION_MINUTES = 30


def expire_payment_reservations():
    now = timezone.now()
    expired_orders = list(
        Order.objects.select_for_update()
        .filter(
            status=Order.Status.PENDING,
            payment_status=Order.PaymentStatus.PENDING,
            payment_method__in=(
                Order.PaymentMethod.CARD,
                Order.PaymentMethod.BANK_TRANSFER,
            ),
        )
        .filter(
            Q(payment_expires_at__lte=now)
            | Q(
                payment_expires_at__isnull=True,
                created_at__lte=now - timedelta(minutes=PAYMENT_RESERVATION_MINUTES),
            )
        )
        .order_by("pk")
        .prefetch_related("items")
    )
    for order in expired_orders:
        items = list(order.items.select_for_update().order_by("product_id"))
        products = {
            product.pk: product
            for product in Product.objects.select_for_update()
            .filter(pk__in=[item.product_id for item in items if item.product_id])
            .order_by("pk")
        }
        for item in items:
            product = products.get(item.product_id)
            if product is not None:
                product.stock += item.quantity
                product.save(update_fields=("stock", "updated_at"))
        order.status = Order.Status.CANCELLED
        order.save(update_fields=("status", "updated_at"))
    return len(expired_orders)
