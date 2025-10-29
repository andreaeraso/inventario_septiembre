from rest_framework import serializers
from .models import Usuario, Dependencia, Recurso, Prestamo, SolicitudPrestamo

# Serializador de Usuario
class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'rol', 'dependencia', 'password']

    def create(self, validated_data):
        user = Usuario.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            rol=validated_data['rol'],
            dependencia=validated_data.get('dependencia')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

# Serializador de Dependencias
class DependenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependencia
        fields = '__all__'

# Serializador de Recursos
class RecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = '__all__'

# Serializador de Préstamos
class PrestamoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    recurso = RecursoSerializer(read_only=True)

    class Meta:
        model = Prestamo
        fields = '__all__'

# Serializador de Solicitudes de Préstamo
class SolicitudPrestamoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    recurso = RecursoSerializer(read_only=True)

    class Meta:
        model = SolicitudPrestamo
        fields = '__all__'
