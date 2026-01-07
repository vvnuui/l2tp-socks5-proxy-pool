"""连接状态 URL 配置"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConnectionCallbackView, ConnectionViewSet

router = DefaultRouter()
router.register(r'connections', ConnectionViewSet, basename='connection')

urlpatterns = [
    path('', include(router.urls)),
    path('connections/<str:action_type>/', ConnectionCallbackView.as_view(), name='connection-callback'),
]
