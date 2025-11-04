from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Dependencia, Recurso, Prestamo, TipoRecurso, SolicitudPrestamo, Notificacion

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('codigo', 'email', 'programa', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('codigo', 'first_name', 'last_name', 'email')
    ordering = ('codigo',)
    
    fieldsets = (
        (None, {'fields': ('codigo', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email', 'foto')}),
        ('Información Académica', {'fields': ('programa', 'rol')}),  # Quité 'codigo' porque ya está en el primero
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('codigo', 'password1', 'password2', 'email', 'programa', 'rol'),
        }),
    )

@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

    # 🔹 Filtra solo los usuarios con rol ADMIN en el desplegable de administrador
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'administrador':
            from .models import Usuario
            kwargs['queryset'] = Usuario.objects.filter(rol=Usuario.ADMIN)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(TipoRecurso)
class TipoRecursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dependencia')
    search_fields = ('nombre',)
    list_filter = ('dependencia',)

@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dependencia', 'disponible')
    list_filter = ('disponible', 'dependencia')
    search_fields = ('nombre', 'descripcion')

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'recurso', 'fecha_prestamo', 'fecha_devolucion', 'devuelto')
    list_filter = ('devuelto', 'fecha_prestamo')
    search_fields = ('usuario__codigo', 'recurso__nombre')  

@admin.register(SolicitudPrestamo)
class SolicitudPrestamoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'recurso', 'estado', 'fecha_solicitud')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('usuario__codigo', 'recurso__nombre')

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'leida', 'fecha')
    list_filter = ('tipo', 'leida')
    search_fields = ('usuario__codigo', 'mensaje')