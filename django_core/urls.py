# django_core/urls.py

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include

from django_core.settings import DEBUG

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_page.urls')), # Страницы.
    path('auth/', include('django.contrib.auth.urls')), # Стандартная аутентификация.
    path('events/', include('app_event.urls')), # События.
]

if DEBUG:
    urlpatterns += staticfiles_urlpatterns()