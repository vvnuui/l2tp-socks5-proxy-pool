"""L2TP 账号 URL 配置"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import L2TPAccountViewSet

router = DefaultRouter()
router.register(r'accounts', L2TPAccountViewSet, basename='account')

urlpatterns = [
    path('', include(router.urls)),
]
