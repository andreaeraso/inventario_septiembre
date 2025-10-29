# prestamos/management/commands/notificar_devolucion.py

from django.core.management.base import BaseCommand
from django.utils.timezone import localdate
from django.core.mail import send_mail
from django.urls import reverse
from datetime import timedelta
from prestamos.models import Prestamo, Notificacion
from django.conf import settings


class Command(BaseCommand):
    help = 'Envía notificaciones de recordatorio y vencimiento de préstamos'

    def handle(self, *args, **kwargs):
        hoy = localdate()
        mañana = hoy + timedelta(days=1)

        # 📌 1. Recordatorios (un día antes)
        prestamos_manana = Prestamo.objects.filter(
            fecha_devolucion__date=mañana,
            devuelto=False
        )

        for prestamo in prestamos_manana:
            usuario = prestamo.usuario
            recurso = prestamo.recurso
            admin_dependencia = recurso.dependencia.administrador

            # Notificación en campanita (usuario y admin)
            Notificacion.objects.create(
                usuario=usuario,
                tipo="VENCIMIENTO",
                mensaje=f"El recurso '{recurso.nombre}' debe devolverse mañana ({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).",
                url=reverse("lista_solicitudes")
            )
            if admin_dependencia:
                Notificacion.objects.create(
                    usuario=admin_dependencia,
                    tipo="VENCIMIENTO",
                    mensaje=f"El recurso '{recurso.nombre}' prestado a {usuario.get_full_name()} vence mañana ({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).",
                    url=reverse("lista_solicitudes")
                )

            # Correo
            if usuario.email:
                send_mail(
                    subject='Recordatorio de devolución de recurso',
                    message=(
                        f"Hola {usuario.get_full_name()},\n\n"
                        f"Recuerda devolver el recurso '{recurso.nombre}' mañana "
                        f"({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).\n\n"
                        "Universidad de Nariño."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=False,
                )

        # 📌 2. Vencidos (hoy)
        prestamos_hoy = Prestamo.objects.filter(
            fecha_devolucion__date=hoy,
            devuelto=False
        )

        for prestamo in prestamos_hoy:
            usuario = prestamo.usuario
            recurso = prestamo.recurso
            admin_dependencia = recurso.dependencia.administrador

            # Notificación en campanita (usuario y admin)
            Notificacion.objects.create(
                usuario=usuario,
                tipo="VENCIDO",
                mensaje=f"⚠️ El recurso '{recurso.nombre}' vence hoy ({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).",
                url=reverse("lista_solicitudes")
            )
            if admin_dependencia:
                Notificacion.objects.create(
                    usuario=admin_dependencia,
                    tipo="VENCIDO",
                    mensaje=f"⚠️ El recurso '{recurso.nombre}' prestado a {usuario.get_full_name()} vence hoy ({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).",
                    url=reverse("lista_solicitudes")
                )

            # Correo
            if usuario.email:
                send_mail(
                    subject='⚠️ Recurso vencido',
                    message=(
                        f"Hola {usuario.get_full_name()},\n\n"
                        f"El recurso '{recurso.nombre}' vence HOY "
                        f"({prestamo.fecha_devolucion.strftime('%d/%m/%Y')}).\n\n"
                        "Por favor devuélvelo cuanto antes.\n\n"
                        "Universidad de Nariño."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=False,
                )
