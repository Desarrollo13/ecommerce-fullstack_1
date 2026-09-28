import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_payment_confirmed_email(order):
    _send_order_email(
        order,
        f"Pago acreditado para tu pedido #{order.pk}",
        f"Recibimos el pago de tu pedido #{order.pk} por ${order.total}. Lo prepararemos a la brevedad.",
    )


def send_order_shipped_email(order):
    _send_order_email(
        order,
        f"Tu pedido #{order.pk} fue despachado",
        f"Tu pedido #{order.pk} fue despachado y esta en camino.",
    )


def send_order_delivered_email(order):
    _send_order_email(
        order,
        f"Tu pedido #{order.pk} fue entregado",
        f"Tu pedido #{order.pk} figura como entregado. Gracias por tu compra.",
    )


def _send_order_email(order, subject, message):
    if not order.user.email:
        return

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("No se pudo enviar un email de pedido")
