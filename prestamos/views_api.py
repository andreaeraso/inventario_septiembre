from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .models import Dependencia, Recurso, Prestamo, Usuario, SolicitudPrestamo
from .serializers import (
    UsuarioSerializer, DependenciaSerializer, RecursoSerializer, 
    PrestamoSerializer, SolicitudPrestamoSerializer
)

# Vista para Usuarios
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    def get_permissions(self):
        if self.action in ['create', 'register']:
            return [AllowAny()]
        return [IsAuthenticated()]

    # Registro de usuario desde la PWA
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UsuarioSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])  # Encriptar contraseña
            user.save()
            return Response({'message': 'Usuario registrado correctamente'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vista para Dependencias
class DependenciaViewSet(viewsets.ModelViewSet):
    queryset = Dependencia.objects.all()
    serializer_class = DependenciaSerializer
    permission_classes = [AllowAny]

# Vista para Recursos
class RecursoViewSet(viewsets.ModelViewSet):
    queryset = Recurso.objects.all()
    serializer_class = RecursoSerializer
    permission_classes = [AllowAny]

# Vista para Préstamos
class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = Prestamo.objects.all()
    serializer_class = PrestamoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mis_prestamos(self, request):
        prestamos = Prestamo.objects.filter(usuario=request.user)
        serializer = self.get_serializer(prestamos, many=True)
        return Response(serializer.data)

# Vista para Solicitudes de Préstamo
class SolicitudPrestamoViewSet(viewsets.ModelViewSet):
    queryset = SolicitudPrestamo.objects.all()
    serializer_class = SolicitudPrestamoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.rol == 'admin':
            return SolicitudPrestamo.objects.all()
        return SolicitudPrestamo.objects.filter(usuario=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.recurso.disponible:
            Prestamo.objects.create(
                usuario=solicitud.usuario,
                recurso=solicitud.recurso,
                fecha_devolucion=solicitud.fecha_devolucion
            )
            solicitud.recurso.disponible = False
            solicitud.recurso.save()
            solicitud.estado = 'Aprobado'
            solicitud.save()
            return Response({'message': 'Préstamo aprobado'}, status=status.HTTP_200_OK)
        return Response({'error': 'El recurso no está disponible'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        solicitud.estado = 'Rechazado'
        solicitud.save()
        return Response({'message': 'Solicitud rechazada'}, status=status.HTTP_200_OK)
