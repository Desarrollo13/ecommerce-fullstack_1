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


def send_password_reset_email(user, reset_url):
    try:
        send_mail(
            "Restablecé tu contraseña",
            "Recibimos una solicitud para restablecer tu contraseña. "
            f"Usá este enlace para elegir una nueva contraseña: {reset_url}\n\n"
            "Si no solicitaste este cambio, podés ignorar este mensaje.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("No se pudo enviar el email de restablecimiento de contraseña")
