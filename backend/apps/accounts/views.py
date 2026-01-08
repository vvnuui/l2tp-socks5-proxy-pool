"""L2TP 账号视图"""

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.logs.models import SystemLog
from apps.network.services import GostService, L2TPService

from .models import L2TPAccount
from .serializers import (
    L2TPAccountCreateSerializer,
    L2TPAccountListSerializer,
    L2TPAccountSerializer,
)


import logging

logger = logging.getLogger(__name__)


class L2TPAccountViewSet(viewsets.ModelViewSet):
    """L2TP 账号管理接口"""

    queryset = L2TPAccount.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['username', 'assigned_ip', 'remark']
    ordering_fields = ['created_at', 'username', 'assigned_ip']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return L2TPAccountListSerializer
        if self.action == 'create':
            return L2TPAccountCreateSerializer
        return L2TPAccountSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f'创建账号请求数据: {request.data}')
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f'创建账号验证失败: {serializer.errors}')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        account = serializer.save()
        # 同步到 chap-secrets（容器内可能不可用）
        try:
            l2tp_service = L2TPService()
            l2tp_service.add_user(account.username, account.password, account.assigned_ip)
        except Exception as e:
            # 在 Docker 容器中可能没有 /etc/ppp 目录，忽略错误
            SystemLog.log('l2tp', f'创建账号 {account.username} 时同步 chap-secrets 失败: {e}', level='warning', account=account)
        SystemLog.log('l2tp', f'创建账号: {account.username}', account=account)

    def perform_update(self, serializer):
        account = serializer.save()
        # 同步到 chap-secrets（容器内可能不可用）
        try:
            l2tp_service = L2TPService()
            l2tp_service.update_user(account.username, account.password, account.assigned_ip)
        except Exception as e:
            SystemLog.log('l2tp', f'更新账号 {account.username} 时同步 chap-secrets 失败: {e}', level='warning', account=account)
        SystemLog.log('l2tp', f'更新账号: {account.username}', account=account)

    @transaction.atomic
    def perform_destroy(self, instance):
        from apps.connections.models import Connection
        from django.utils import timezone

        l2tp_service = L2TPService()

        # 1. 终止活跃的 PPP 连接
        try:
            active_conn = Connection.objects.filter(
                account=instance,
                status='online'
            ).first()
            if active_conn:
                # 终止 PPP 连接
                l2tp_service.terminate_connection(active_conn.interface)
                # 更新连接状态
                active_conn.status = 'offline'
                active_conn.disconnected_at = timezone.now()
                active_conn.save()
                SystemLog.log('l2tp', f'终止连接: {active_conn.interface}', account=instance)
        except Exception as e:
            SystemLog.log_error('l2tp', f'终止连接失败: {e}', account=instance)

        # 2. 停止代理
        try:
            if instance.proxy_config and instance.proxy_config.is_running:
                gost_service = GostService()
                gost_service.stop(instance.proxy_config.listen_port)
        except Exception:
            pass

        # 3. 从 chap-secrets 删除
        try:
            l2tp_service.remove_user(instance.username)
        except Exception:
            pass

        SystemLog.log('l2tp', f'删除账号: {instance.username}')
        instance.delete()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换账号启用状态"""
        account = self.get_object()
        account.is_active = not account.is_active
        account.save()

        # 同步到 chap-secrets（容器内可能不可用）
        try:
            l2tp_service = L2TPService()
            if account.is_active:
                l2tp_service.add_user(account.username, account.password, account.assigned_ip)
            else:
                l2tp_service.remove_user(account.username)
        except Exception:
            pass

        SystemLog.log('l2tp', f'账号状态变更: {account.username} -> {"启用" if account.is_active else "禁用"}',
                      account=account)

        return Response({'is_active': account.is_active})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取账号统计"""
        total = L2TPAccount.objects.count()
        active = L2TPAccount.objects.filter(is_active=True).count()
        online = L2TPAccount.objects.filter(connections__status='online').distinct().count()

        return Response({
            'total': total,
            'active': active,
            'inactive': total - active,
            'online': online
        })

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建账号"""
        count = request.data.get('count', 1)
        prefix = request.data.get('prefix', 'user')

        if count < 1 or count > 100:
            return Response({'error': '数量必须在 1-100 之间'}, status=status.HTTP_400_BAD_REQUEST)

        created = []

        for i in range(count):
            next_ip = L2TPAccount.get_next_available_ip()
            if not next_ip:
                break

            username = f'{prefix}_{L2TPAccount.objects.count() + 1}'
            password = L2TPAccount.objects.make_random_password() if hasattr(L2TPAccount.objects, 'make_random_password') else f'pass_{i}'

            account = L2TPAccount.objects.create(
                username=username,
                password=password,
                assigned_ip=next_ip
            )

            # 同步到 chap-secrets（容器内可能不可用）
            try:
                l2tp_service = L2TPService()
                l2tp_service.add_user(username, password, next_ip)
            except Exception:
                pass

            # 创建代理配置
            from apps.network.models import ProxyConfig, RoutingTable

            port = ProxyConfig.get_next_available_port()
            if port:
                ProxyConfig.objects.create(account=account, listen_port=port)

            table_id = RoutingTable.get_next_table_id()
            RoutingTable.objects.create(
                account=account,
                table_id=table_id,
                table_name=f'rt_user_{account.id}'
            )

            created.append({
                'id': account.id,
                'username': username,
                'password': password,
                'assigned_ip': next_ip,
                'proxy_port': port
            })

        return Response({'created': len(created), 'accounts': created})
