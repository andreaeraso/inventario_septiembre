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
from datetime import timedelta



from .models import Dependencia, Recurso, Prestamo, Usuario, SolicitudPrestamo, Notificacion, Recurso, TipoRecurso

# Vista de inicio
@login_required
def inicio(request):
    from django.core.exceptions import ObjectDoesNotExist

    try:
        if request.user.rol == 'admin':
            # Verificar que tenga dependencia asignada
            dependencia = request.user.dependencia_administrada

            context = {
                'total_recursos': Recurso.objects.filter(dependencia=dependencia).count(),
                'prestamos_activos': Prestamo.objects.filter(
                    recurso__dependencia=dependencia,
                    devuelto=False
                ).count(),
                'prestamos_recientes': Prestamo.objects.filter(
                    recurso__dependencia=dependencia
                ).order_by('-fecha_prestamo')[:10]
            }
            return render(request, 'admin/dashboard.html', context)

        elif request.user.rol in ['profesor', 'estudiante']:
            prestamos_aprobados = (
                Prestamo.objects
                .filter(usuario=request.user)
                .select_related('recurso')
                .order_by('-fecha_prestamo')  # 👈 Orden descendente por fecha de préstamo
            )

            context = {
                'mis_prestamos': prestamos_aprobados
            }

            if request.user.rol == 'profesor':
                return render(request, 'profesor/dashboard.html', context)
            else:
                return render(request, 'estudiante/dashboard.html', context)

    except ObjectDoesNotExist:
        #Si no tiene dependencia asignada u otro problema relacional
        messages.error(
            request,
            "⚠️ Error al iniciar sesión. Tu cuenta no tiene una dependencia asignada. Contacta al administrador.",
            extra_tags='error_login'
        )
        return redirect("login_registro")  

        

def login_registro_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')  # Para diferenciar login o registro

        # ================== REGISTRO ==================
        if form_type == 'registro':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            codigo = request.POST.get('codigo')
            programa = request.POST.get('programa')
            rol = request.POST.get('rol')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            foto = request.FILES.get('foto')

            # Validaciones
            if password1 != password2:
                messages.error(request, "❌ Las contraseñas no coinciden")
            elif Usuario.objects.filter(email=email).exists():
                messages.error(request, "❌ El correo electrónico ya está registrado")
            elif Usuario.objects.filter(codigo=codigo).exists():
                messages.error(request, "❌ El código ya está registrado")
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
                    messages.success(request, "Ahora inicia sesión.", extra_tags='success_register')
                except Exception as e:
                    messages.error(request, f"⚠️ Error al crear el usuario: {str(e)}")

        # ================== LOGIN ==================
        elif form_type == 'login':
            codigo = request.POST.get('codigo')
            password = request.POST.get('password')

            user = authenticate(request, username=codigo, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"👋 Bienvenido {user.first_name} {user.last_name}")  # 👈 mensaje de éxito
                return redirect("inicio")
            else:
                messages.error(request, "❌ Código o contraseña incorrectos", extra_tags="error_login")
                return redirect("login_registro")  # 👈 redirige a la misma vista

    return render(request, 'login_registro.html')


from django.http import JsonResponse

def check_email(request):
    email = request.GET.get("valor", "")
    exists = Usuario.objects.filter(email=email).exists()
    return JsonResponse({
        "exists": exists,
        "message": "El correo ya está registrado" if exists else "Correo disponible"
    })

def check_codigo(request):
    codigo = request.GET.get("valor", "")
    exists = Usuario.objects.filter(codigo=codigo).exists()
    return JsonResponse({
        "exists": exists,
        "message": "El código ya está registrado" if exists else "Código disponible"
    })


# Vista para cerrar sesión
def logout_view(request):
    logout(request)
    return redirect("login_registro")   


from collections import defaultdict, OrderedDict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
@login_required
def inventario(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')

    recursos_queryset = Recurso.objects.filter(
        dependencia=request.user.dependencia_administrada
    )

    total_recursos = recursos_queryset.count()

    recursos_agrupados = defaultdict(list)
    for recurso in recursos_queryset:
        recursos_agrupados[recurso.tipo].append(recurso)

    for tipo in recursos_agrupados:
        recursos_agrupados[tipo] = sorted(recursos_agrupados[tipo], key=lambda r: r.nombre.lower())

    recursos_ordenados = OrderedDict(
        sorted(recursos_agrupados.items(), key=lambda item: item[0].nombre.lower())
    )

    return render(request, 'admin/inventario/lista.html', {
        'recursos': recursos_ordenados,
        'total_recursos': total_recursos
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

@login_required
def perfil_usuario(request):
    usuario = request.user

    if usuario.rol == "admin":
        template_name = "admin/perfil.html"
    elif usuario.rol == "estudiante":
        template_name = "estudiante/perfil.html"
    elif usuario.rol == "profesor":
        template_name = "profesor/perfil.html"
    else:
        template_name = "perfil.html"

    # 🔹 Solo el propio usuario puede editar su información aquí
    puede_editar = True

    return render(request, template_name, {'usuario': usuario, 'puede_editar': puede_editar})


@login_required
def perfil_usuario_detalle(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)

    # ⚠️ Solo el propio usuario puede editar sus datos
    puede_editar = (request.user.id == usuario.id)

    if usuario.rol == "admin":
        template_name = "admin/perfil.html"
    elif usuario.rol == "estudiante":
        template_name = "estudiante/perfil.html"
    elif usuario.rol == "profesor":
        template_name = "profesor/perfil.html"
    else:
        template_name = "perfil.html"

    # 🔒 Si no es el dueño del perfil y no es superusuario, no puede editar
    if not puede_editar and not request.user.is_superuser:
        # Si el admin quiere solo visualizar, ok; pero no editar
        puede_editar = False

    return render(request, template_name, {'usuario': usuario, 'puede_editar': puede_editar})



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

        # 📌 Guardar la ruta antigua antes de reemplazar
        foto_antigua = usuario.foto.path if usuario.foto else None

        # 📷 Asignar la nueva foto
        usuario.foto = nueva_foto
        usuario.save()

        # 🧹 Eliminar la foto anterior si existe y es diferente
        if foto_antigua and os.path.exists(foto_antigua):
            try:
                os.remove(foto_antigua)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar la foto anterior: {e}")

        return redirect('perfil_usuario')

    return redirect('perfil_usuario')

from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def guardar_cedula_telefono(request):
    usuario = request.user

    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        telefono = request.POST.get('telefono')

        # VALIDAR CÉDULA DUPLICADA
        if cedula:
            existe = User.objects.filter(cedula=cedula).exclude(id=usuario.id).exists()
            if existe:
                messages.error(
                    request,
                    "Esta cédula ya está registrada por otro usuario.",
                    extra_tags='error'
                )
                return redirect('perfil_usuario')

        try:
            if cedula:
                usuario.cedula = cedula
            if telefono:
                usuario.telefono = telefono

            usuario.save()

            messages.success(
                request,
                "Información actualizada correctamente.",
                extra_tags='update_success'
            )
            return redirect('perfil_usuario')

        except IntegrityError:
            # 🔒 Seguridad extra por unique=True
            messages.error(
                request,
                "No se pudo guardar: la cédula ya existe en el sistema.",
                extra_tags='error'
            )
            return redirect('perfil_usuario')

    return redirect('perfil_usuario')


@login_required
def agregar_recurso(request):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    dependencia = request.user.dependencia_administrada

    if request.method == 'POST':
        id_recurso = request.POST.get('id', '').strip()
        tipo_id = request.POST.get('tipo', '').strip()  # este será el ID del tipo o "nuevo"

        if tipo_id == "nuevo":
            nuevo_tipo_nombre = request.POST.get('nuevo_tipo', '').strip()
            tipo_obj, created = TipoRecurso.objects.get_or_create(
                nombre=nuevo_tipo_nombre,
                dependencia=dependencia
            )
        else:
            tipo_obj = TipoRecurso.objects.get(id=tipo_id)

        nombre = request.POST.get('nombre', '').strip()
        foto = request.FILES.get('foto', None)
        descripcion = request.POST.get('descripcion', '').strip()

        if not (id_recurso and tipo_obj and nombre and descripcion):
            messages.error(request, 'Todos los campos son obligatorios excepto la foto')
            return redirect('agregar_recurso')

        try:
            Recurso.objects.create(
                id=id_recurso,
                tipo=tipo_obj,
                nombre=nombre,
                foto=foto,
                descripcion=descripcion,
                dependencia=dependencia
            )
            messages.success(request, 'Recurso agregado exitosamente')
            return redirect('inventario')
        except Exception as e:
            messages.error(request, f'Error al crear el recurso: {str(e)}')

    # Obtener tipos de la dependencia
    tipos_existentes = TipoRecurso.objects.filter(dependencia=dependencia).order_by('nombre')

    return render(request, 'admin/inventario/agregar.html', {
        'tipos_existentes': tipos_existentes
    })


from django.http import JsonResponse
from .models import Recurso
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Recurso


@login_required
def validar_id_recurso(request):
    """
    Endpoint AJAX para validar si un ID/QR ya existe.
    Parámetros GET:
      - id: ID a validar (obligatorio)
      - actual: ID del recurso actualmente en edición (opcional) -> se excluye de la búsqueda
    Devuelve JSON: {'existe': True|False}
    """
    id_recurso = request.GET.get('id', '').strip()
    recurso_actual = request.GET.get('actual', '').strip() or None

    existe = False
    if id_recurso:
        qs = Recurso.objects.filter(id=id_recurso)
        if recurso_actual:
            qs = qs.exclude(id=recurso_actual)
        existe = qs.exists()

    return JsonResponse({'existe': existe})



@login_required
def editar_recurso(request, recurso_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')

    recurso = get_object_or_404(
        Recurso,
        id=recurso_id,
        dependencia=request.user.dependencia_administrada
    )

    if request.method == 'POST':
        try:
            nuevo_id = request.POST.get('id', '').strip()
            tipo_id = request.POST.get('tipo', '').strip()

            # Si se seleccionó "nuevo", usar el campo nuevo_tipo
            if tipo_id == "nuevo":
                tipo_nombre = request.POST.get('nuevo_tipo', '').strip()
                if not tipo_nombre:
                    messages.error(request, 'Debe ingresar un nombre para el nuevo tipo de recurso.')
                    return redirect('editar_recurso', recurso_id=recurso.id)
                tipo, _ = TipoRecurso.objects.get_or_create(
                    nombre=tipo_nombre,
                    dependencia=request.user.dependencia_administrada
                )
            else:
                tipo = TipoRecurso.objects.get(id=tipo_id)

            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            nueva_foto = request.FILES.get('foto', None)

            if not (nuevo_id and tipo and nombre and descripcion):
                messages.error(request, 'Todos los campos obligatorios deben ser completados.')
                return redirect('editar_recurso', recurso_id=recurso.id)

            # 📸 Guardar referencia de la foto anterior solo si llega una nueva
            foto_anterior = recurso.foto.path if (nueva_foto and recurso.foto) else None

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
                    foto=nueva_foto if nueva_foto else recurso.foto
                )
                nuevo_recurso.save()
                recurso.delete()

                # 🧹 Solo eliminar la foto anterior si se subió una nueva
                if foto_anterior and os.path.exists(foto_anterior):
                    try:
                        os.remove(foto_anterior)
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar la foto anterior: {e}")

                messages.success(request, 'Recurso actualizado exitosamente con un nuevo ID.')
                return redirect('inventario')

            # Si no cambia el ID, actualizar campos
            recurso.tipo = tipo
            recurso.nombre = nombre
            recurso.descripcion = descripcion

            # 📸 Si hay una nueva foto, eliminar la anterior
            if nueva_foto:
                if recurso.foto and os.path.exists(recurso.foto.path):
                    try:
                        os.remove(recurso.foto.path)
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar la foto anterior: {e}")
                recurso.foto = nueva_foto

            recurso.save()
            messages.success(request, 'Recurso actualizado exitosamente.')
            return redirect('inventario')

        except Exception as e:
            messages.error(request, f'Error al actualizar el recurso: {str(e)}')

    # 🔹 Obtener los tipos existentes
    tipos_existentes = TipoRecurso.objects.filter(
        dependencia=request.user.dependencia_administrada
    ).order_by('nombre')

    # 🔹 Verificar si el tipo del recurso está en la lista
    tipo_actual = recurso.tipo
    tipo_en_lista = tipos_existentes.filter(id=tipo_actual.id).exists()

    # 🔹 Enviar flags al template
    contexto = {
        'recurso': recurso,
        'tipos_existentes': tipos_existentes,
        'tipo_en_lista': tipo_en_lista,
        'tipo_nombre': tipo_actual.nombre if not tipo_en_lista else '',
    }

    return render(request, 'admin/inventario/editar.html', contexto)



@login_required
def eliminar_recurso(request, recurso_id):
    if request.user.rol != 'admin':
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('inicio')
    
    recurso = get_object_or_404(Recurso, id=recurso_id, dependencia=request.user.dependencia_administrada)
    
    if request.method == 'POST':
        try:
            # Guardamos la ruta absoluta de la imagen antes de eliminar el recurso
            if recurso.foto and os.path.isfile(recurso.foto.path):
                os.remove(recurso.foto.path)

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

    # ✅ Ordenar los tipos de recurso alfabéticamente por su nombre
    recursos_ordenados = OrderedDict(
        sorted(recursos_agrupados.items(), key=lambda item: item[0].nombre.lower())
    )

    # 📅 Calcular mínimo de fecha de préstamo (5 días)
    min_fecha_prestamo = timezone.localdate() + timedelta(days=5)

    # ✅ NUEVO: obtener los recursos con solicitud pendiente del usuario actual
    solicitudes_pendientes = SolicitudPrestamo.objects.filter(
        usuario=request.user,
        estado=SolicitudPrestamo.PENDIENTE
    ).values_list('recurso_id', flat=True)

    return render(request, 'prestamo/recursos_dependencia.html', {
        'dependencia': dependencia,
        'recursos': recursos_ordenados,
        'min_fecha_prestamo': min_fecha_prestamo.isoformat(),
        'solicitudes_pendientes': list(solicitudes_pendientes),  # 👈 se pasa al template
    })


##########################################################################################

from django.core.mail import send_mail
from .models import Notificacion, SolicitudPrestamo, Prestamo, Recurso


# Crear solicitud de préstamo (estudiante/profesor)
@login_required
def solicitar_prestamo(request, recurso_id):
    recurso = get_object_or_404(Recurso, id=recurso_id)

    if request.method == 'POST':
        fecha_devolucion_str = request.POST.get('fecha_devolucion')

        # Validar formato fecha
        try:
            fecha_devolucion = datetime.strptime(fecha_devolucion_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, "La fecha seleccionada no es válida.")
            return redirect('recursos_por_dependencia', dependencia_id=recurso.dependencia.id)

        # 📌 Requerir que la fecha sea >= 5 dias
        hoy = timezone.localdate()
        minima_fecha = hoy + timedelta(days=5)
        if fecha_devolucion < minima_fecha:
            messages.error(request, f"La fecha de devolución debe ser al menos {minima_fecha.strftime('%d/%m/%Y')}.")
            return redirect('recursos_por_dependencia', dependencia_id=recurso.dependencia.id)


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
            Notificacion.objects.create(
                usuario=admin_user,
                tipo="SOLICITUD",
                mensaje=f"El usuario {request.user.get_full_name()} ha solicitado el préstamo del recurso '{recurso.nombre}'."
            )

            if admin_user.email:
                send_mail(
                    subject="Nueva solicitud de préstamo de recurso",
                    message=(
                        f"Estimado {admin_user.get_full_name()},\n\n"
                        f"El usuario {request.user.get_full_name()} ha registrado una solicitud de préstamo "
                        f"para el recurso: '{recurso.nombre}'.\n\n"
                        "Por favor, revise la plataforma para aprobar o rechazar esta solicitud.\n\n"
                        "Atentamente,\nSistema de Préstamos UDENAR"
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
        messages.error(request, "El recurso no está disponible.", extra_tags="recurso_no_disponible")
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
    if request.user.rol != 'admin':
        return redirect('inicio')

    solicitudes = SolicitudPrestamo.objects.select_related('recurso', 'usuario').filter(
        recurso__dependencia=request.user.dependencia_administrada
    ).order_by('-fecha_solicitud')

    # Filtrar los mensajes: solo mostrar los del tipo 'recurso_no_disponible'
    mensajes_filtrados = []
    for message in messages.get_messages(request):
        if 'recurso_no_disponible' in message.tags:
            mensajes_filtrados.append(message)

    context = {
        'solicitudes': solicitudes,
        'mensajes_filtrados': mensajes_filtrados
    }

    return render(request, 'admin/solicitudes_prestamo.html', context)


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
        solicitudes = (
            SolicitudPrestamo.objects
            .filter(
                recurso__dependencia=request.user.dependencia_administrada,
                estado=estado_map[estado]
            )
            .select_related('recurso', 'usuario')   # 🔹 Optimiza las consultas
            .order_by('-fecha_solicitud')           # 🔹 Orden descendente
        )
        template = f'admin/solicitudes_{estado}.html'

    elif request.user.rol in ["estudiante", "profesor"]:
        solicitudes = (
            SolicitudPrestamo.objects
            .filter(
                usuario=request.user,
                estado=estado_map[estado]
            )
            .select_related('recurso')              # 🔹 Optimiza para cargar el nombre del recurso
            .order_by('-fecha_solicitud')           # 🔹 Más recientes primero
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

@login_required
def extender_prestamo(request, prestamo_id):
    if request.user.rol != "admin":
        return redirect('inicio')

    prestamo = get_object_or_404(Prestamo, id=prestamo_id, devuelto=False)

    if request.method == "POST":
        nueva_fecha_str = request.POST.get("nueva_fecha")
        if not nueva_fecha_str:
            messages.error(request, "Debe seleccionar una nueva fecha de devolución.")
            return redirect("prestamos_lista")

        nueva_fecha = datetime.strptime(nueva_fecha_str, "%Y-%m-%d")

        # 📌 Actualizar fecha de devolución del préstamo que se va a cerrar
        prestamo.fecha_devolucion = datetime.now()  # la fecha desde la cual se aprueba la extensión
        prestamo.devuelto = True
        prestamo.save()

        recurso = prestamo.recurso
        usuario = prestamo.usuario
        dependencia = recurso.dependencia
        admin_dependencia = dependencia.administrador

        # 2. Firmas y encabezado
        firma_usuario_path = usuario.firma.path if usuario.firma else None
        firma_admin_path = admin_dependencia.firma.path if admin_dependencia and admin_dependencia.firma else None
        escudo_path = os.path.join(settings.MEDIA_ROOT, 'encabezado_contratos', 'escudo.png')
        escudo_url = f'file://{escudo_path}'

        context = {
            'usuario': usuario,
            'recurso': recurso,
            'administrador': admin_dependencia,
            'dependencia': admin_dependencia.dependencia_administrada if admin_dependencia else None,
            'firma_usuario_path': f'file://{firma_usuario_path}' if firma_usuario_path else None,
            'firma_admin_path': f'file://{firma_admin_path}' if firma_admin_path else None,
            'escudo_path': escudo_url,
            'fecha': datetime.now(),
            'fecha_devolucion': nueva_fecha,
        }

        # 3. Generar nuevo PDF
        html_string = render_to_string('contrato/contrato_prestamo.html', context)
        html = HTML(string=html_string)

        nombre_archivo = f'contrato_extension_{prestamo.id}_{int(datetime.now().timestamp())}.pdf'
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_contratos')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, nombre_archivo)

        html.write_pdf(temp_path)

        destino_prestamo = os.path.join(settings.MEDIA_ROOT, 'contratos_prestamo', nombre_archivo)
        os.makedirs(os.path.dirname(destino_prestamo), exist_ok=True)
        shutil.copyfile(temp_path, destino_prestamo)

        # 4. Crear nuevo préstamo
        nuevo_prestamo = Prestamo.objects.create(
            usuario=usuario,
            recurso=recurso,
            fecha_devolucion=nueva_fecha,
            contrato_prestamo=f'contratos_prestamo/{nombre_archivo}'
        )

        # 5. Limpiar temp
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

        # 6. Notificación al usuario
        Notificacion.objects.create(
            usuario=usuario,
            tipo="EXTENSION",
            mensaje=f"Su préstamo del recurso '{recurso.nombre}' ha sido extendido hasta {nueva_fecha.date()}."
        )

        messages.success(request, f"El préstamo ha sido extendido hasta {nueva_fecha.date()}.")
        return redirect("inicio")

    return redirect("inicio")

def pwa_login(request):
    return render(request, "mobile/login.html")

def pwa_registro(request):
    return render(request, "mobile/registro.html")

def pwa_inicio(request):
    return render(request, "mobile/inicio.html")

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
from django.db.models.functions import ExtractWeekDay, ExtractHour, ExtractMonth
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import Prestamo, Recurso

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, F
from django.db.models.functions import ExtractWeekDay, ExtractHour, ExtractMonth
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import render, redirect
from datetime import timedelta
from .models import Prestamo, Recurso


from django.db.models import Count
from django.db.models.functions import ExtractWeekDay, ExtractHour, ExtractMonth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import Prestamo, Recurso

@login_required
def estadisticas(request):
    # Solo el admin puede acceder
    if request.user.rol != 'admin':
        messages.error(request, "No tienes permiso para acceder a las estadísticas.")
        return redirect("inicio")

    # Verificar que el admin tenga una dependencia asignada
    dependencia = getattr(request.user, "dependencia_administrada", None)
    if not dependencia:
        messages.warning(request, "No tienes una dependencia asignada. Contacta al administrador general.")
        return redirect("inicio")

    # 🔍 Filtrar todos los datos por dependencia
    prestamos = Prestamo.objects.filter(recurso__dependencia=dependencia)
    recursos = Recurso.objects.filter(dependencia=dependencia)

    hoy = now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year

    # 📊 Totales de préstamos
    prestamos_total = prestamos.count()
    prestamos_mes = prestamos.filter(
        fecha_prestamo__year=anio_actual,
        fecha_prestamo__month=mes_actual
    ).count()

    # 📦 Recursos disponibles y prestados
    recursos_disponibles = recursos.filter(disponible=True).count()
    recursos_prestados = recursos.filter(disponible=False).count()
    total_recursos = recursos_disponibles + recursos_prestados
    tasa_uso_inventario = round((recursos_prestados / total_recursos) * 100, 1) if total_recursos > 0 else 0

    # 🏆 Recursos más prestados
    recursos_populares = (
        prestamos.values("recurso__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # 👥 Usuarios más activos
    usuarios_activos = (
        prestamos.values("usuario__first_name", "usuario__last_name")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # 📈 Promedio de duración del préstamo
    if prestamos_total > 0:
        duraciones = [
            (p.fecha_devolucion.date() - p.fecha_prestamo.date()).days
            for p in prestamos
        ]
        promedio_duracion = round(sum(duraciones) / len(duraciones), 1) if duraciones else 0
    else:
        promedio_duracion = 0

    # ✅ Devoluciones y retrasos reales
    devueltos = prestamos.filter(devuelto=True).count()
    no_devueltos = prestamos.filter(devuelto=False).count()

    # Retrasos: no devueltos con fecha_devolucion vencida
    prestamos_vencidos = prestamos.filter(
        devuelto=False,
        fecha_devolucion__lt=now()
    ).count()

    tasa_devoluciones = round((devueltos / prestamos_total) * 100, 1) if prestamos_total > 0 else 0
    tasa_retrasos = round((prestamos_vencidos / prestamos_total) * 100, 1) if prestamos_total > 0 else 0

    # 📅 Préstamos por día de la semana
    prestamos_por_dia = (
        prestamos.annotate(dia=ExtractWeekDay('fecha_prestamo'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    dias_semana = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    prestamos_por_dia = [
        {'dia': dias_semana[p['dia'] - 1], 'total': p['total']}
        for p in prestamos_por_dia
    ]

    # 🕒 Horas pico
    prestamos_por_hora = (
        prestamos.annotate(hora=ExtractHour('fecha_prestamo'))
        .values('hora')
        .annotate(total=Count('id'))
        .order_by('hora')
    )

    # 📆 Evolución mensual del año actual
    prestamos_mensuales = (
        prestamos.filter(fecha_prestamo__year=anio_actual)
        .annotate(mes=ExtractMonth('fecha_prestamo'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    prestamos_mensuales = [
        {'mes': meses[p['mes'] - 1], 'total': p['total']}
        for p in prestamos_mensuales
    ]

    # 🔁 Rotación de recursos
    rotacion_recursos = round(prestamos_total / total_recursos, 2) if total_recursos > 0 else 0

    # 👤 Usuarios recurrentes del mes
    usuarios_recurrentes = (
        prestamos.filter(fecha_prestamo__month=mes_actual)
        .values('usuario')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .count()
    )
    total_usuarios_mes = prestamos.filter(
        fecha_prestamo__month=mes_actual
    ).values('usuario').distinct().count()
    tasa_reincidencia = round(
        (usuarios_recurrentes / total_usuarios_mes) * 100, 1
    ) if total_usuarios_mes > 0 else 0

    # 📊 Contexto final
    contexto = {
        "dependencia": dependencia,
        "prestamos_total": prestamos_total,
        "prestamos_mes": prestamos_mes,
        "recursos_disponibles": recursos_disponibles,
        "recursos_prestados": recursos_prestados,
        "tasa_uso_inventario": tasa_uso_inventario,
        "rotacion_recursos": rotacion_recursos,
        "recursos_populares": recursos_populares,
        "usuarios_activos": usuarios_activos,
        "promedio_duracion": promedio_duracion,
        "tasa_devoluciones": tasa_devoluciones,
        "tasa_retrasos": tasa_retrasos,
        "tasa_reincidencia": tasa_reincidencia,
        "prestamos_por_dia": prestamos_por_dia,
        "prestamos_por_hora": prestamos_por_hora,
        "prestamos_mensuales": prestamos_mensuales,
    }

    return render(request, "prestamo/estadisticas.html", contexto)








from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.timezone import now
from .models import Prestamo

@login_required
def mis_prestamos(request):
    """
    Vista para mostrar los préstamos del usuario logueado (estudiante o profesor)
    """
    usuario = request.user

    # Solo los roles estudiante o profesor pueden acceder
    if usuario.rol not in ['estudiante', 'profesor']:
        messages.error(request, "Solo los estudiantes o profesores pueden acceder a esta vista.")
        return redirect('inicio')

    prestamos = (
        Prestamo.objects
        .filter(usuario=usuario)
        .select_related('recurso')
        .order_by('-fecha_prestamo')  # 🔽 Más recientes primero
    )

    contexto = {
        'prestamos': prestamos,
        'titulo': 'Mis Préstamos',
    }
    return render(request, 'prestamo/mis_prestamos.html', contexto)

@login_required
def lista_prestamos(request):
    """
    Vista para mostrar los préstamos de la dependencia del administrador.
    """
    usuario = request.user

    # 1️⃣ Verificar que sea administrador
    if usuario.rol != 'admin':
        messages.error(request, "No tienes permiso para acceder a esta vista.")
        return redirect('inicio')

    # 2️⃣ Obtener dependencia administrada correctamente
    dependencia_admin = getattr(usuario, 'dependencia_administrada', None)

    # 3️⃣ Si no tiene dependencia asignada y no es superusuario, mostrar aviso
    if not dependencia_admin and not usuario.is_superuser:
        messages.warning(request, "No tienes una dependencia asignada. Contacta al administrador general.")
        prestamos = Prestamo.objects.none()
        titulo = "Préstamos (Sin dependencia asignada)"
    else:
        # 4️⃣ Si es superuser -> ve todo, si no -> solo su dependencia
        if usuario.is_superuser:
            prestamos = (
                Prestamo.objects
                .select_related('usuario', 'recurso', 'recurso__dependencia')
                .order_by('-fecha_prestamo')
            )
            titulo = "Todos los préstamos (Administrador global)"
        else:
            prestamos = (
                Prestamo.objects
                .select_related('usuario', 'recurso', 'recurso__dependencia')
                .filter(recurso__dependencia=dependencia_admin)
                .order_by('-fecha_prestamo')
            )
            titulo = f"Préstamos de la Dependencia: {dependencia_admin.nombre}"

    contexto = {
        'prestamos': prestamos,
        'titulo': titulo,
    }

    return render(request, 'prestamo/lista_prestamos.html', contexto)
