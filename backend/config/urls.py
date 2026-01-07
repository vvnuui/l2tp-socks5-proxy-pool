"""URL configuration for L2TP Socks5 Proxy Pool Manager"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.connections.urls')),
    path('api/', include('apps.network.urls')),
    path('api/', include('apps.logs.urls')),
]
