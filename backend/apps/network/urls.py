"""网络配置 URL"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, ProxyConfigViewSet, RoutingTableViewSet, ServerConfigView

router = DefaultRouter()
router.register(r'proxies', ProxyConfigViewSet, basename='proxy')
router.register(r'routing-tables', RoutingTableViewSet, basename='routing-table')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('server-config/', ServerConfigView.as_view(), name='server-config'),
]
