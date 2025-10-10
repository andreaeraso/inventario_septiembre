"""
URL configuration for core project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin
from django.http import HttpResponse
from pathlib import Path


# === Vista para servir el manifest.json en la raíz ===
def manifest(request):
    manifest_path = Path(settings.BASE_DIR) / "static" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = f.read()
    return HttpResponse(data, content_type="application/manifest+json")


# === Rutas principales ===
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('prestamos.urls')),  # Tu app principal
    path('api-auth/', include('rest_framework.urls')),
    path('manifest.json', manifest, name='manifest'),  # Manifest PWA
]

# === Archivos multimedia ===
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
