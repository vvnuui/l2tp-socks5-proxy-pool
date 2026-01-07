"""连接状态 URL 配置"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConnectionViewSet, PPPCallbackView

router = DefaultRouter()
router.register(r'connections', ConnectionViewSet, basename='connection')

urlpatterns = [
    # PPP 回调必须放在 router 之前，否则会被匹配为 /connections/<pk>/
    path('ppp/callback/', PPPCallbackView.as_view(), name='ppp-callback'),
    path('', include(router.urls)),
]
