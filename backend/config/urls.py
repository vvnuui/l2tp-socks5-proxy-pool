"""URL configuration for L2TP Socks5 Proxy Pool Manager"""

from django.contrib import admin
from django.urls import include, path

from apps.accounts.auth_views import LoginView, LogoutView, UserInfoView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/user/', UserInfoView.as_view(), name='user-info'),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.connections.urls')),
    path('api/', include('apps.network.urls')),
    path('api/', include('apps.logs.urls')),
]
