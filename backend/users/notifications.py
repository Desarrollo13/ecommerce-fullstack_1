import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_welcome_email(user):
    if not user.email:
        return

    try:
        send_mail(
            "Bienvenido/a a Mercado local",
            "Tu cuenta fue creada correctamente. Ya podes iniciar sesion y realizar compras.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("No se pudo enviar el email de bienvenida")
