from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Importación de vistas para la API REST
from .views_api import UsuarioViewSet, DependenciaViewSet, RecursoViewSet, PrestamoViewSet

# Importación de vistas para la interfaz web
from .views import ( logout_view, inicio, login_registro_view, inventario, crear_prestamo, prestamos_pendientes,
    solicitar_prestamo, agregar_recurso, editar_recurso, eliminar_recurso,
    recursos_no_disponibles, prestamos_lista, nuevo_prestamo, prestamos_activos,
    historial_prestamos, editar_prestamo, marcar_devuelto, lista_dependencias, 
    recursos_por_dependencia, lista_solicitudes, aprobar_solicitud, rechazar_solicitud,
    mis_solicitudes, solicitudes_por_estado, perfil_usuario, pwa_inicio,pwa_login,pwa_registro,
    subir_firma, subir_foto, guardar_cedula_telefono, perfil_usuario_detalle, obtener_notificaciones, 
    marcar_notificacion_leida, estadisticas, extender_prestamo,
)

# Configuración de las rutas de la API REST con Django Rest Framework
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'dependencias', DependenciaViewSet)
router.register(r'recursos', RecursoViewSet)
router.register(r'prestamos', PrestamoViewSet)

urlpatterns = [
    # Endpoints para autenticación con JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Endpoints de la API REST
    path('api/', include(router.urls)),
    
    # Autenticación de usuarios
    path('', login_registro_view, name='home'),
    path('cuenta/', login_registro_view, name='login_registro'),
    path('logout/', logout_view, name='logout'),
    
    # Página de inicio
    path('inicio/', inicio, name='inicio'),
    
    # Gestión del inventario
    path('inventario/', inventario, name='inventario'),
    path('inventario/agregar/', agregar_recurso, name='agregar_recurso'),
    path('inventario/editar/<int:recurso_id>/', editar_recurso, name='editar_recurso'),
    path('inventario/eliminar/<int:recurso_id>/', eliminar_recurso, name='eliminar_recurso'),
    path('inventario/no-disponibles/', recursos_no_disponibles, name='recursos_no_disponibles'),
    
    # Gestión de dependencias y recursos asociados
    path('prestamo/dependencias/', lista_dependencias, name='lista_dependencias'),
    path('dependencia/<int:dependencia_id>/recursos/', recursos_por_dependencia, name='recursos_por_dependencia'),
    
    # Solicitudes de préstamo
    path('solicitar_prestamo/<int:recurso_id>/', solicitar_prestamo, name='solicitar_prestamo'),
    path('solicitudes/', lista_solicitudes, name='lista_solicitudes'),
    path('solicitudes/aprobar/<int:solicitud_id>/', aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/rechazar/<int:solicitud_id>/', rechazar_solicitud, name='rechazar_solicitud'),
    path('mis-solicitudes/', mis_solicitudes, name='mis_solicitudes'),
    path('solicitudes/<str:estado>/', solicitudes_por_estado, name='solicitudes_por_estado'),
    
    # Perfil de usuario
    path('perfil/', perfil_usuario, name='perfil_usuario'),
    path('perfil/subir-firma/', subir_firma, name='subir_firma'), #subir firma
    path('perfil/subir-foto/', subir_foto, name='subir_foto'),
    path('perfil/guardar-cedula-telefono/', guardar_cedula_telefono, name='guardar_cedula_telefono'),
    path('perfil/<int:usuario_id>/', perfil_usuario_detalle, name='perfil_usuario_detalle'),
    
    
    path("notificaciones/", obtener_notificaciones, name="obtener_notificaciones"),
    path("notificaciones/leida/", marcar_notificacion_leida, name="marcar_notificacion_leida"),
    path("estadisticas/", estadisticas, name="estadisticas"),


    
    # Gestión de préstamos
    path('prestamos/', prestamos_lista, name='prestamos_lista'),
    path('prestamos/nuevo/', nuevo_prestamo, name='nuevo_prestamo'),
    path('prestamos/activos/', prestamos_activos, name='prestamos_activos'),
    path('prestamos/historial/', historial_prestamos, name='historial_prestamos'),
    path('prestamos/editar/<int:prestamo_id>/', editar_prestamo, name='editar_prestamo'),
    path('prestamos/devolver/<int:prestamo_id>/', marcar_devuelto, name='marcar_devuelto'),
    path('prestamos/extender/<int:prestamo_id>/', extender_prestamo, name='extender_prestamo'),

    
    path('pwa/login/', pwa_login, name='pwa_login'),
    path('pwa/registro/', pwa_registro, name='pwa_registro'),
    path('pwa/inicio/', pwa_inicio, name='pwa_inicio'),
    path("manifest.json", TemplateView.as_view(template_name="manifest.json", content_type="application/json")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Configuración para servir archivos estáticos en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)