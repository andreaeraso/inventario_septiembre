from django.core.management.base import BaseCommand
from django.utils.timezone import localdate
from django.core.mail import send_mail
from datetime import timedelta
from prestamos.models import Prestamo

class Command(BaseCommand):
    help = 'Envía notificaciones un día antes de la fecha de devolución del recurso'

    def handle(self, *args, **kwargs):
        mañana = localdate() + timedelta(days=1)
        prestamos = Prestamo.objects.filter(
            fecha_devolucion__date=mañana,
            devuelto=False
        )

        for prestamo in prestamos:
            usuario = prestamo.usuario
            recurso = prestamo.recurso

            if usuario.email:
                send_mail(
                    subject='Recordatorio de devolución de recurso',
                    message=(
                        f"Hola {usuario.get_full_name()},\n\n"
                        f"Este es un recordatorio de que debes devolver el recurso '{recurso.nombre}' "
                        f"el día {prestamo.fecha_devolucion.strftime('%d/%m/%Y')}.\n"
                        "Por favor acércate al punto de entrega para evitar inconvenientes.\n\n"
                        "Universidad de Nariño."
                    ),
                    from_email='noreply@unad.edu.co',  # asegúrate que esté configurado correctamente
                    recipient_list=[usuario.email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Correo enviado a {usuario.email}"))
            else:
                self.stdout.write(self.style.WARNING(f"El usuario {usuario} no tiene correo registrado."))
