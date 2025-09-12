import os
import shutil
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.files import File
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Count
from weasyprint import HTML
from django.utils import timezone



from .models import Dependencia, Recurso, Prestamo, Usuario, SolicitudPrestamo, Notificacion, Recurso

# Vista de inicio
@login_required
def inicio(request):
    if request.user.rol == 'admin':
        context = {
            'total_recursos': Recurso.objects.filter(dependencia=request.user.dependencia_administrada).count(),
            'prestamos_activos': Prestamo.objects.filter(
                recurso__dependencia=request.user.dependencia_administrada,
                devuelto=False
            ).count(),
            'prestamos_recientes': Prestamo.objects.filter(
                recurso__dependencia=request.user.dependencia_administrada
            ).order_by('-fecha_prestamo')[:10]
        }
        return render(request, 'admin/dashboard.html', context)

    elif request.user.rol in ['profesor', 'estudiante']:
        # Obtener los préstamos aprobados y activos (no devueltos)
        prestamos_aprobados = Prestamo.objects.filter(usuario=request.user).select_related('recurso')

        context = {
            'mis_prestamos': prestamos_aprobados
        }

        if request.user.rol == 'profesor':
            return render(request, 'profesor/dashboard.html', context)
        else:
            return render(request, 'estudiante/dashboard.html', context)
        
        
def login_registro_view(request):
    if request.method == 'POST':
        if 'form_type' in request.POST and request.POST['form_type'] == 'registro':
            # -------- REGISTRO --------
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            codigo = request.POST.get('codigo')
            programa = request.POST.get('programa')
            rol = request.POST.get('rol')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            foto = request.FILES.get('foto')

            if password1 != password2:
                messages.error(request, "Las contraseñas no coinciden")
            elif Usuario.objects.filter(email=email).exists():
                messages.error(request, "El correo electrónico ya está registrado")
            elif Usuario.objects.filter(codigo=codigo).exists():
                messages.error(request, "El código ya está registrado")
            else:
                try:
                    usuario = Usuario.objects.create(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        codigo=codigo,
                        programa=programa,
                        rol=rol,
                        foto=foto,
                    )
                    usuario.set_password(password1)
                    usuario.save()
                    messages.success(request, "Registro exitoso. Ahora inicia sesión.")
                except Exception as e:
                    messages.error(request, f"Error al crear el usuario: {str(e)}")

        elif 'form_type' in request.POST and request.POST['form_type'] == 'login':
            # -------- LOGIN --------
            codigo = request.POST.get('codigo')
            password = request.POST.get('password')
            user = authenticate(request, username=codigo, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Inicio de sesión exitoso")
                return redirect("inicio")
            else:
                messages.error(request, "Código o contraseña incorrectos")

    return render(request, 'login_registro.html')

# Vista para cerrar sesión
def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente")
    return redirect("login_registro")  # Redirige al login después de cerrar sesión

# Vista de recursos por dependencia
@login_required
def inventario(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')

    recursos_queryset = Recurso.objects.filter(dependencia=request.user.dependencia_administrada)

    # Agrupar y ordenar
    recursos_agrupados = defaultdict(list)
    for recurso in recursos_queryset:
        recursos_agrupados[recurso.tipo].append(recurso)

    # Ordenar los recursos dentro de cada tipo por nombre
    for tipo in recursos_agrupados:
        recursos_agrupados[tipo] = sorted(recursos_agrupados[tipo], key=lambda r: r.nombre.lower())

    # Ordenar los tipos de recurso alfabéticamente
    recursos_ordenados = OrderedDict(sorted(recursos_agrupados.items(), key=lambda item: item[0].lower()))

    return render(request, 'admin/inventario/lista.html', {
        'recursos': recursos_ordenados
    })

@login_required
def perfil_usuario(request):
    usuario = request.user
    
    if usuario.rol == "admin":  # Asumiendo que el admin tiene `is_staff=True`
        template_name = "admin/perfil.html"
    elif usuario.rol == "estudiante":  # Ajusta el nombre del campo `rol` si es diferente
        template_name = "estudiante/perfil.html"
    elif usuario.rol == "profesor":
        template_name = "profesor/perfil.html"
    else:
        template_name = "perfil.html"  # Un fallback por si acaso

    return render(request, template_name, {'usuario': usuario})


@login_required
def perfil_usuario_detalle(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if usuario.rol == "admin":
        template_name = "admin/perfil.html"
    elif usuario.rol == "estudiante":
        template_name = "estudiante/perfil.html"
    elif usuario.rol == "profesor":
        template_name = "profesor/perfil.html"
    else:
        template_name = "perfil.html"

    return render(request, template_name, {'usuario': usuario})


@login_required
def subir_firma(request):
    if request.method == 'POST':
        firma = request.FILES.get('firma')
        if firma:
            if not firma.name.endswith('.png'):
                messages.error(request, 'La firma debe estar en formato PNG.')
                return redirect('perfil_usuario')  # ajusta con tu nombre de URL
            usuario = request.user
            if not usuario.firma:
                usuario.firma = firma
                usuario.save()
                messages.success(request, 'Firma subida correctamente.')
            else:
                messages.warning(request, 'Ya has subido una firma.')
    return redirect('perfil_usuario')

@login_required
def subir_foto(request):
    usuario = request.user
    if request.method == 'POST' and request.FILES.get('foto'):
        nueva_foto = request.FILES['foto']
        
        # Eliminar foto anterior si existe
        if usuario.foto:
            if os.path.isfile(usuario.foto.path):
                os.remove(usuario.foto.path)

        usuario.foto = nueva_foto
        usuario.save()
        return redirect('perfil_usuario')  # Asegúrate de tener una URL llamada 'perfil'

    return redirect('perfil_usuario')

@login_required
def guardar_cedula_telefono(request):
    if request.method == 'POST':
        usuario = request.user
        cedula = request.POST.get('cedula')
        telefono = request.POST.get('telefono')

        if cedula and not usuario.cedula:
            usuario.cedula = cedula
        if telefono and not usuario.telefono:
            usuario.telefono = telefono

        usuario.save()
        messages.success(request, "Información actualizada correctamente.")
    return redirect('perfil_usuario')  # Asegúrate que esta URL apunte al perfil

@login_required
def agregar_recurso(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    if request.method == 'POST':
        id_recurso = request.POST.get('id', '').strip()
        tipo = request.POST.get('tipo', '').strip()

        # Si seleccionaron "nuevo", usar el valor del campo nuevo_tipo
        if tipo == "nuevo":
            tipo = request.POST.get('nuevo_tipo', '').strip()

        nombre = request.POST.get('nombre', '').strip()
        foto = request.FILES.get('foto', None)
        descripcion = request.POST.get('descripcion', '').strip()
        dependencia = request.user.dependencia_administrada

        if not (id_recurso and tipo and nombre and descripcion):
            messages.error(request, 'Todos los campos son obligatorios excepto la foto')
            return redirect('agregar_recurso')

        try:
            Recurso.objects.create(
                id=id_recurso,
                tipo=tipo,
                nombre=nombre,
                foto=foto,
                descripcion=descripcion,
                dependencia=dependencia
            )
            messages.success(request, 'Recurso agregado exitosamente')
            return redirect('inventario')
        except Exception as e:
            messages.error(request, f'Error al crear el recurso: {str(e)}')

    # Obtener tipos ya existentes
    tipos_existentes = Recurso.objects.values_list('tipo', flat=True).distinct().order_by('tipo')

    return render(request, 'admin/inventario/agregar.html', {
        'tipos_existentes': tipos_existentes
    })


@login_required
def editar_recurso(request, recurso_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')

    recurso = get_object_or_404(Recurso, id=recurso_id, dependencia=request.user.dependencia_administrada)

    if request.method == 'POST':
        try:
            nuevo_id = request.POST.get('id', '').strip()
            tipo = request.POST.get('tipo', '').strip()

            # Si se seleccionó "nuevo", usar el campo nuevo_tipo
            if tipo == "nuevo":
                tipo = request.POST.get('nuevo_tipo', '').strip()

            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            foto = request.FILES.get('foto', None)

            # Validaciones mínimas
            if not (nuevo_id and tipo and nombre and descripcion):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('editar_recurso', recurso_id=recurso.id)

            # Si el usuario cambia el ID
            if nuevo_id and str(nuevo_id) != str(recurso.id):
                if Recurso.objects.filter(id=nuevo_id).exists():
                    messages.error(request, 'El ID ya está en uso por otro recurso.')
                    return redirect('editar_recurso', recurso_id=recurso.id)

                nuevo_recurso = Recurso(
                    id=nuevo_id,
                    tipo=tipo,
                    nombre=nombre,
                    descripcion=descripcion,
                    dependencia=recurso.dependencia,
                    disponible=recurso.disponible,
                )

                if foto:
                    nuevo_recurso.foto = foto
                else:
                    nuevo_recurso.foto = recurso.foto

                nuevo_recurso.save()
                recurso.delete()

                messages.success(request, 'Recurso actualizado exitosamente con un nuevo ID.')
                return redirect('inventario')

            # Si no cambia el ID, solo actualiza los campos
            recurso.tipo = tipo
            recurso.nombre = nombre
            recurso.descripcion = descripcion
            if foto:
                recurso.foto = foto
            recurso.save()

            messages.success(request, 'Recurso actualizado exitosamente.')
            return redirect('inventario')

        except Exception as e:
            messages.error(request, f'Error al actualizar el recurso: {str(e)}')

    # Enviar tipos únicos al template
    tipos_existentes = Recurso.objects.values_list('tipo', flat=True).distinct().order_by('tipo')

    return render(request, 'admin/inventario/editar.html', {
        'recurso': recurso,
        'tipos_existentes': tipos_existentes
    })


@login_required
def eliminar_recurso(request, recurso_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    recurso = get_object_or_404(Recurso, id=recurso_id, dependencia=request.user.dependencia_administrada)
    
    if request.method == 'POST':
        try:
            recurso.delete()
            messages.success(request, 'Recurso eliminado exitosamente')
        except Exception as e:
            messages.error(request, f'Error al eliminar el recurso: {str(e)}')
    
    return redirect('inventario')

@login_required
def recursos_no_disponibles(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    recursos = Recurso.objects.filter(
        dependencia=request.user.dependencia_administrada,
        disponible=False
    )
    return render(request, 'admin/inventario/no_disponibles.html', {'recursos': recursos})

# Vista para crear un préstamo
@login_required
def crear_prestamo(request, recurso_id):
    recurso = get_object_or_404(Recurso, id=recurso_id, disponible=True)
    if request.method == 'POST':
        fecha_devolucion = request.POST.get('fecha_devolucion')
        firma = request.FILES.get('firma')
        Prestamo.objects.create(
            usuario=request.user,
            recurso=recurso,
            fecha_devolucion=fecha_devolucion,
            firmado=firma
        )
        recurso.disponible = False
        recurso.save()
        return redirect('inicio')
    return render(request, 'crear_prestamo.html', {'recurso': recurso})

# Vista para ver préstamos pendientes
@login_required
def prestamos_pendientes(request):
    prestamos = Prestamo.objects.filter(usuario=request.user, devuelto=False)
    return render(request, 'prestamos_pendientes.html', {'prestamos': prestamos})


#####################################################################################

# Vistas de Préstamos
@login_required
def prestamos_lista(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    prestamos = Prestamo.objects.filter(
        recurso__dependencia=request.user.dependencia_administrada
    ).order_by('-fecha_prestamo')
    return render(request, 'admin/prestamos/lista.html', {'prestamos': prestamos})

@login_required
def nuevo_prestamo(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    if request.method == 'POST':
        try:
            usuario = Usuario.objects.get(id=request.POST['usuario'])
            recurso = Recurso.objects.get(
                id=request.POST['recurso'],
                dependencia=request.user.dependencia_administrada,
                disponible=True
            )
            
            prestamo = Prestamo.objects.create(
                usuario=usuario,
                recurso=recurso,
                fecha_devolucion=request.POST['fecha_devolucion']
            )
            
            recurso.disponible = False
            recurso.save()
            
            messages.success(request, 'Préstamo registrado exitosamente')
            return redirect('prestamos_lista')
        except Exception as e:
            messages.error(request, f'Error al crear el préstamo: {str(e)}')
    
    context = {
        'usuarios': Usuario.objects.filter(rol__in=['estudiante', 'profesor']),
        'recursos': Recurso.objects.filter(dependencia=request.user.dependencia_administrada, disponible=True)
    }
    return render(request, 'admin/prestamos/nuevo.html', context)

@login_required
def prestamos_activos(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    prestamos = Prestamo.objects.filter(
        recurso__dependencia=request.user.dependencia_administrada,
        devuelto=False
    ).order_by('fecha_devolucion')
    
    context = {
        'prestamos': prestamos,
        'now': timezone.now()
    }
    return render(request, 'admin/prestamos/activos.html', context)

@login_required
def historial_prestamos(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    prestamos = Prestamo.objects.filter(
        recurso__dependencia=request.user.dependencia_administrada,
        devuelto=True
    ).order_by('-fecha_prestamo')
    return render(request, 'admin/prestamos/historial.html', {'prestamos': prestamos})

@login_required
def editar_prestamo(request, prestamo_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    prestamo = get_object_or_404(
        Prestamo,
        id=prestamo_id,
        recurso__dependencia=request.user.dependencia_administrada
    )
    
    if request.method == 'POST':
        try:
            prestamo.fecha_devolucion = request.POST['fecha_devolucion']
            prestamo.save()
            messages.success(request, 'Préstamo actualizado exitosamente')
            return redirect('prestamos_lista')
        except Exception as e:
            messages.error(request, f'Error al actualizar el préstamo: {str(e)}')
    
    return render(request, 'admin/prestamos/editar.html', {'prestamo': prestamo})



@login_required
def lista_dependencias(request):
    # Esta lista se muestra en la página del profesor/estudiante al darle solicitar préstamo
    if request.user.rol not in ['estudiante', 'profesor']:
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')

    dependencias = Dependencia.objects.all().order_by('nombre')  # ordenadas A-Z
    return render(request, 'prestamo/lista_dependencias.html', {'dependencias': dependencias})


@login_required
def recursos_por_dependencia(request, dependencia_id): 
    dependencia = get_object_or_404(Dependencia, id=dependencia_id)
    recursos_queryset = Recurso.objects.filter(dependencia=dependencia)

    # Agrupar los recursos por tipo
    recursos_agrupados = defaultdict(list)
    for recurso in recursos_queryset:
        recursos_agrupados[recurso.tipo].append(recurso)

    # Ordenar los recursos dentro de cada tipo por nombre
    for tipo in recursos_agrupados:
        recursos_agrupados[tipo] = sorted(recursos_agrupados[tipo], key=lambda r: r.nombre.lower())

    # Ordenar los tipos de recurso alfabéticamente
    recursos_ordenados = OrderedDict(sorted(recursos_agrupados.items(), key=lambda item: item[0].lower()))

    return render(request, 'prestamo/recursos_dependencia.html', {
        'dependencia': dependencia,
        'recursos': recursos_ordenados
    })

##########################################################################################

from django.core.mail import send_mail
from .models import Notificacion, SolicitudPrestamo, Prestamo, Recurso


# Crear solicitud de préstamo (estudiante/profesor)
@login_required
def solicitar_prestamo(request, recurso_id):
    recurso = get_object_or_404(Recurso, id=recurso_id)

    if request.method == 'POST':
        fecha_devolucion = request.POST.get('fecha_devolucion')

        # Crear la solicitud de préstamo
        solicitud = SolicitudPrestamo.objects.create(
            recurso=recurso,
            usuario=request.user,
            fecha_devolucion=fecha_devolucion,
            estado=SolicitudPrestamo.PENDIENTE
        )

        # Buscar administrador de la dependencia
        admin_user = recurso.dependencia.administrador

        if admin_user:
            # 📌 Notificación en el sistema
            Notificacion.objects.create(
                usuario=admin_user,
                tipo="SOLICITUD",
                mensaje=f"El usuario {request.user.get_full_name()} ha solicitado el préstamo del recurso '{recurso.nombre}'."
            )

            # 📌 Notificación por correo
            if admin_user.email:
                send_mail(
                    subject="Nueva solicitud de préstamo de recurso",
                    message=(
                        f"Estimado {admin_user.get_full_name()},\n\n"
                        f"El usuario {request.user.get_full_name()} ha registrado una solicitud de préstamo "
                        f"para el recurso: '{recurso.nombre}'.\n\n"
                        "Por favor, revise la plataforma para aprobar o rechazar esta solicitud.\n\n"
                        "Atentamente,\nSistema de Préstamos UNAD"
                    ),
                    from_email="noreply@unad.edu.co",
                    recipient_list=[admin_user.email],
                    fail_silently=True
                )

    return redirect('recursos_por_dependencia', dependencia_id=recurso.dependencia.id)


# Aprobar solicitud (administrador)
@login_required
def aprobar_solicitud(request, solicitud_id):
    if request.user.rol != "admin":
        return redirect('inicio')

    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)

    if not solicitud.recurso.disponible:
        messages.error(request, "El recurso no está disponible.")
        return redirect('lista_solicitudes')

    recurso = solicitud.recurso
    dependencia = recurso.dependencia
    admin_dependencia = dependencia.administrador

    # Firmas y PDF (igual que lo tienes)
    dependencia_admin = admin_dependencia.dependencia_administrada if admin_dependencia else None
    firma_usuario_path = solicitud.usuario.firma.path if solicitud.usuario.firma else None
    firma_admin_path = admin_dependencia.firma.path if admin_dependencia and admin_dependencia.firma else None
    escudo_path = os.path.join(settings.MEDIA_ROOT, 'encabezado_contratos', 'escudo.png')
    escudo_url = f'file://{escudo_path}'

    context = {
        'solicitud': solicitud,
        'usuario': solicitud.usuario,
        'recurso': recurso,
        'administrador': admin_dependencia,
        'dependencia': dependencia_admin,
        'firma_usuario_path': f'file://{firma_usuario_path}' if firma_usuario_path else None,
        'firma_admin_path': f'file://{firma_admin_path}' if firma_admin_path else None,
        'escudo_path': escudo_url,
        'fecha': datetime.now(),
    }

    html_string = render_to_string('contrato/contrato_prestamo.html', context)
    html = HTML(string=html_string)

    nombre_archivo = f'contrato_prestamo_{solicitud.id}.pdf'
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_contratos')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, nombre_archivo)

    html.write_pdf(temp_path)

    with open(temp_path, 'rb') as pdf_file:
        solicitud.contrato_solicitud.save(nombre_archivo, File(pdf_file), save=False)

    solicitud.estado = SolicitudPrestamo.APROBADO
    solicitud.save()

    destino_prestamo = os.path.join(settings.MEDIA_ROOT, 'contratos_prestamo', nombre_archivo)
    os.makedirs(os.path.dirname(destino_prestamo), exist_ok=True)
    shutil.copyfile(temp_path, destino_prestamo)

    Prestamo.objects.create(
        usuario=solicitud.usuario,
        recurso=recurso,
        fecha_devolucion=solicitud.fecha_devolucion,
        contrato_prestamo=f'contratos_prestamo/{nombre_archivo}'
    )

    recurso.disponible = False
    recurso.save()

    if os.path.exists(temp_path):
        os.remove(temp_path)

    if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
        os.rmdir(temp_dir)

    # 📌 Notificación al solicitante
    Notificacion.objects.create(
        usuario=solicitud.usuario,
        tipo="APROBADA",
        mensaje=f"Su solicitud de préstamo del recurso '{solicitud.recurso.nombre}' ha sido aprobada por {request.user.get_full_name()}."
    )

    if solicitud.usuario.email:
        send_mail(
            subject="Solicitud de préstamo aprobada",
            message=(
                f"Estimado {solicitud.usuario.get_full_name()},\n\n"
                f"Nos complace informarle que su solicitud de préstamo del recurso '{solicitud.recurso.nombre}' "
                f"ha sido aprobada por el administrador {request.user.get_full_name()}.\n\n"
                "Adjunto encontrará el contrato en la plataforma.\n\n"
                "Atentamente,\nSistema de Préstamos UDENAR"
            ),
            from_email="noreply@unad.edu.co",
            recipient_list=[solicitud.usuario.email],
            fail_silently=True
        )

    return redirect('lista_solicitudes')


# Rechazar solicitud (administrador)
@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.user.rol != "admin":
        return redirect('inicio')

    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)
    solicitud.estado = SolicitudPrestamo.RECHAZADO
    solicitud.save()

    # 📌 Notificación al solicitante
    Notificacion.objects.create(
        usuario=solicitud.usuario,
        tipo="RECHAZADA",
        mensaje=f"Su solicitud de préstamo del recurso '{solicitud.recurso.nombre}' fue rechazada por {request.user.get_full_name()}."
    )

    if solicitud.usuario.email:
        send_mail(
            subject="Solicitud de préstamo rechazada",
            message=(
                f"Estimado {solicitud.usuario.get_full_name()},\n\n"
                f"Lamentamos informarle que su solicitud de préstamo para el recurso '{solicitud.recurso.nombre}' "
                f"ha sido rechazada por el administrador {request.user.get_full_name()}.\n\n"
                "Atentamente,\nSistema de Préstamos UDENAR"
            ),
            from_email="noreply@unad.edu.co",
            recipient_list=[solicitud.usuario.email],
            fail_silently=True
        )

    return redirect('lista_solicitudes')


@login_required
def obtener_notificaciones(request):
    # Traemos todas las notificaciones filtradas primero
    notificaciones_qs = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')

    # Calculamos no leídas ANTES del slice
    no_leidas = notificaciones_qs.filter(leida=False)

    # Ahora sí limitamos a las 10 más recientes
    notificaciones = notificaciones_qs[:10]

    data = {
        "total": no_leidas.count(),
        "notificaciones": [
            {
                "id": n.id,
                "mensaje": n.mensaje,
                "tipo": n.tipo,
                "fecha": n.fecha.strftime("%d/%m/%Y %H:%M"),
                "leida": n.leida
            }
            for n in notificaciones
        ]
    }
    return JsonResponse(data)


@login_required
def marcar_notificacion_leida(request):
    if request.method == "POST":
        noti_id = request.POST.get("id")
        try:
            noti = Notificacion.objects.get(id=noti_id, usuario=request.user)
            noti.leida = True
            noti.save()
            return JsonResponse({"ok": True})
        except Notificacion.DoesNotExist:
            return JsonResponse({"ok": False}, status=404)
    return JsonResponse({"ok": False}, status=400)





#Lista para que el administrador pueda ver las solicitudes
@login_required
def lista_solicitudes(request):
    if request.user.rol != 'admin':  # Asegurar que solo los administradores accedan
        return redirect('inicio')

    # Filtrar solicitudes de préstamo solo de la dependencia administrada por el usuario
    solicitudes = SolicitudPrestamo.objects.select_related('recurso', 'usuario').filter(
        recurso__dependencia=request.user.dependencia_administrada
    ).order_by('-fecha_solicitud')

    return render(request, 'admin/solicitudes_prestamo.html', {'solicitudes': solicitudes})


#Lista para que el estudiante pueda ver sus solicitudes
@login_required
def mis_solicitudes(request):
    if request.user.rol != "estudiante":  # Solo permitir a estudiantes
        return redirect('inicio')

    solicitudes = SolicitudPrestamo.objects.filter(usuario=request.user).select_related('recurso').order_by('-fecha_solicitud')

    return render(request, 'estudiante/mis_solicitudes.html', {'solicitudes': solicitudes})


@login_required
def solicitudes_por_estado(request, estado):
    # Asegurar que el estado sea correcto según el modelo
    estado_map = {
        'pendiente': SolicitudPrestamo.PENDIENTE,
        'aprobado': SolicitudPrestamo.APROBADO,
        'rechazado': SolicitudPrestamo.RECHAZADO
    }

    if estado not in estado_map:
        messages.error(request, "Estado inválido.")
        return redirect('inicio')

    # Filtrar según el rol del usuario
    if request.user.rol == "admin":
        solicitudes = SolicitudPrestamo.objects.filter(
            recurso__dependencia=request.user.dependencia_administrada,
            estado=estado_map[estado]
        )
        template = f'admin/solicitudes_{estado}.html'

    elif request.user.rol in ["estudiante", "profesor"]:
        solicitudes = SolicitudPrestamo.objects.filter(
            usuario=request.user,
            estado=estado_map[estado]
        )
        template = f'{request.user.rol}/solicitudes_{estado}.html'

    else:
        return redirect('inicio')

    return render(request, template, {'solicitudes': solicitudes})


@login_required
def marcar_devuelto(request, prestamo_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if request.method == "POST":
        if prestamo.devuelto:
            messages.warning(request, 'Este préstamo ya estaba marcado como devuelto.')
        else:
            try:
                prestamo.devuelto = True
                prestamo.fecha_devolucion = timezone.now()
                prestamo.save()

                prestamo.recurso.disponible = True
                prestamo.recurso.save()

                messages.success(request, 'Préstamo marcado como devuelto exitosamente.')
            except Exception as e:
                messages.error(request, f'Error al marcar el préstamo como devuelto: {str(e)}')

    return redirect('inicio')

def pwa_login(request):
    return render(request, "mobile/login.html")

def pwa_registro(request):
    return render(request, "mobile/registro.html")

def pwa_inicio(request):
    return render(request, "mobile/inicio.html")
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.timezone import now
from django.shortcuts import render, redirect
from django.contrib import messages

@login_required
def estadisticas(request):
    if request.user.rol != 'admin':
        messages.error(request, "No tienes permiso para acceder a las estadísticas")
        return redirect("inicio")

    hoy = now()
    mes_actual = hoy.month
    anio_actual = hoy.year

    # 📌 Total de préstamos en el mes actual
    prestamos_mes = Prestamo.objects.filter(
        fecha_prestamo__year=anio_actual,
        fecha_prestamo__month=mes_actual
    ).count()

    # 📌 Recursos más prestados (TOP 5)
    recursos_populares = (
        Prestamo.objects.values("recurso__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # 📌 Dependencias con más préstamos
    dependencias_populares = (
        Prestamo.objects.values("recurso__dependencia__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # 📌 Usuarios más activos (TOP 5)
    usuarios_activos = (
        Prestamo.objects.values("usuario__first_name", "usuario__last_name")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    contexto = {
        "prestamos_mes": prestamos_mes,
        "recursos_populares": recursos_populares,
        "dependencias_populares": dependencias_populares,
        "usuarios_activos": usuarios_activos,
    }

    return render(request, "prestamo/estadisticas.html", contexto)
