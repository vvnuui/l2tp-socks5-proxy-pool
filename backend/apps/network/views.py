"""网络配置视图"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import L2TPAccount
from apps.connections.models import Connection
from apps.logs.models import SystemLog

from .models import ProxyConfig, RoutingTable
from .serializers import (
    DashboardStatsSerializer,
    ProxyConfigCreateSerializer,
    ProxyConfigSerializer,
    RoutingTableSerializer,
)
from .services import GostService, RoutingService


class ProxyConfigViewSet(viewsets.ModelViewSet):
    """代理配置管理接口"""

    queryset = ProxyConfig.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_running', 'auto_start']
    ordering_fields = ['listen_port', 'created_at']
    ordering = ['listen_port']

    def get_serializer_class(self):
        if self.action == 'create':
            return ProxyConfigCreateSerializer
        return ProxyConfigSerializer

    def get_queryset(self):
        return super().get_queryset().select_related('account')

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动代理"""
        proxy = self.get_object()
        account = proxy.account

        if proxy.is_running:
            return Response({'error': '代理已在运行'}, status=status.HTTP_400_BAD_REQUEST)

        if not account.is_online:
            return Response({'error': '账号未在线'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            connection = account.current_connection
            gost_service = GostService()
            pid = gost_service.start(
                port=proxy.listen_port,
                bind_ip=account.assigned_ip,
                interface=connection.interface
            )

            proxy.gost_pid = pid
            proxy.is_running = True
            proxy.save()

            return Response({
                'message': '代理启动成功',
                'pid': pid,
                'port': proxy.listen_port
            })

        except Exception as e:
            SystemLog.log_error('proxy', f'启动代理失败: {e}', account=account)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止代理"""
        proxy = self.get_object()

        if not proxy.is_running:
            return Response({'error': '代理未在运行'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gost_service = GostService()
            gost_service.stop(proxy.listen_port)

            proxy.gost_pid = None
            proxy.is_running = False
            proxy.save()

            return Response({'message': '代理停止成功'})

        except Exception as e:
            SystemLog.log_error('proxy', f'停止代理失败: {e}', account=proxy.account)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """重启代理"""
        proxy = self.get_object()
        account = proxy.account

        if not account.is_online:
            return Response({'error': '账号未在线'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            connection = account.current_connection
            gost_service = GostService()
            pid = gost_service.restart(
                port=proxy.listen_port,
                bind_ip=account.assigned_ip,
                interface=connection.interface
            )

            proxy.gost_pid = pid
            proxy.is_running = True
            proxy.save()

            return Response({
                'message': '代理重启成功',
                'pid': pid
            })

        except Exception as e:
            SystemLog.log_error('proxy', f'重启代理失败: {e}', account=account)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取代理状态"""
        proxy = self.get_object()
        gost_service = GostService()
        status_info = gost_service.get_status(proxy.listen_port)

        # 同步状态
        if status_info['running'] != proxy.is_running:
            proxy.is_running = status_info['running']
            proxy.gost_pid = status_info['pid']
            proxy.save()

        return Response(status_info)

    @action(detail=False, methods=['get'])
    def running(self, request):
        """获取所有运行中的代理"""
        proxies = ProxyConfig.get_running_proxies()
        serializer = self.get_serializer(proxies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def start_all(self, request):
        """启动所有可用代理"""
        gost_service = GostService()
        started = 0
        failed = 0

        for proxy in ProxyConfig.objects.filter(is_running=False, auto_start=True):
            account = proxy.account
            if not account.is_online:
                continue

            try:
                connection = account.current_connection
                pid = gost_service.start(
                    port=proxy.listen_port,
                    bind_ip=account.assigned_ip,
                    interface=connection.interface
                )
                proxy.gost_pid = pid
                proxy.is_running = True
                proxy.save()
                started += 1
            except Exception:
                failed += 1

        return Response({'started': started, 'failed': failed})

    @action(detail=False, methods=['post'])
    def stop_all(self, request):
        """停止所有运行中的代理"""
        gost_service = GostService()
        stopped = 0

        for proxy in ProxyConfig.objects.filter(is_running=True):
            try:
                gost_service.stop(proxy.listen_port)
                proxy.gost_pid = None
                proxy.is_running = False
                proxy.save()
                stopped += 1
            except Exception:
                pass

        return Response({'stopped': stopped})


class RoutingTableViewSet(viewsets.ReadOnlyModelViewSet):
    """路由表查看接口"""

    queryset = RoutingTable.objects.all()
    serializer_class = RoutingTableSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']

    def get_queryset(self):
        return super().get_queryset().select_related('account')


class DashboardView(APIView):
    """看板数据接口"""

    def get(self, request):
        """获取看板统计数据"""
        accounts_total = L2TPAccount.objects.count()
        accounts_active = L2TPAccount.objects.filter(is_active=True).count()
        connections_online = Connection.objects.filter(status='online').count()
        proxies_running = ProxyConfig.objects.filter(is_running=True).count()

        # 获取 PPP 接口列表（容器内可能没有 ip 命令，需要捕获异常）
        ppp_interfaces = []
        try:
            routing_service = RoutingService()
            ppp_interfaces = routing_service.list_ppp_interfaces()
        except Exception:
            # 在 Docker 容器中可能没有网络工具，忽略错误
            pass

        # 最近连接
        recent_connections = Connection.objects.filter(status='online').select_related('account')[:10]

        return Response({
            'stats': {
                'accounts_total': accounts_total,
                'accounts_active': accounts_active,
                'connections_online': connections_online,
                'proxies_running': proxies_running
            },
            'ppp_interfaces': ppp_interfaces,
            'recent_connections': [
                {
                    'id': c.id,
                    'username': c.account.username,
                    'interface': c.interface,
                    'local_ip': c.local_ip,
                    'connected_at': c.connected_at
                }
                for c in recent_connections
            ]
        })
