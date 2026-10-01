
from django.contrib import admin
from django.urls import include, path

# Rutas principales del proyecto: admin Django y API JSON de ConectaAPI.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('APIConnectApp.urls')),
]
