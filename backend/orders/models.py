from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        CASH_ON_DELIVERY = "cash_on_delivery", "Cash on delivery"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    class PaymentProvider(models.TextChoices):
        MERCADO_PAGO = "mercadopago", "Mercado Pago"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    shipping_address = models.CharField(max_length=500, default="")
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CARD
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    payment_provider = models.CharField(
        max_length=20, choices=PaymentProvider.choices, blank=True, default=""
    )
    provider_preference_id = models.CharField(max_length=100, blank=True, default="")
    provider_payment_id = models.CharField(max_length=100, blank=True, default="")
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="order_total_non_negative",
            )
        ]

    def can_transition_to(self, new_status):
        allowed_transitions = {
            self.Status.PENDING: {self.Status.PROCESSING, self.Status.CANCELLED},
            self.Status.PROCESSING: {self.Status.SHIPPED, self.Status.CANCELLED},
            self.Status.SHIPPED: {self.Status.DELIVERED},
            self.Status.DELIVERED: set(),
            self.Status.CANCELLED: set(),
        }
        return new_status in allowed_transitions.get(self.status, set())

    def can_transition_payment_to(self, new_status):
        allowed_transitions = {
            self.PaymentStatus.PENDING: {
                self.PaymentStatus.PAID,
                self.PaymentStatus.FAILED,
            },
            self.PaymentStatus.PAID: {self.PaymentStatus.REFUNDED},
            self.PaymentStatus.FAILED: {self.PaymentStatus.PAID},
            self.PaymentStatus.REFUNDED: set(),
        }
        return new_status in allowed_transitions.get(self.payment_status, set())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="order_item_unit_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="order_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="order_item_line_total_non_negative",
            ),
        ]
