from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/proctor/health/', lambda r: JsonResponse({'status': 'ok'})),
    path('api/proctor/', include('proctor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
