"""网络配置视图"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import L2TPAccount
from apps.connections.models import Connection
from apps.logs.models import SystemLog

from .models import ProxyConfig, RoutingTable, ServerConfig
from .serializers import (
    DashboardStatsSerializer,
    ProxyConfigCreateSerializer,
    ProxyConfigSerializer,
    RoutingTableSerializer,
    ServerConfigSerializer,
)
from .services import GostService, IPDetectService, RoutingService


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
            routing_table = account.routing_table

            # IP 说明:
            # connection.peer_ip = 服务器 PPP IP (如 10.0.0.1)，Gost 绑定此 IP
            # connection.local_ip = 客户端分配的 IP (如 10.0.0.2)，流量路由到此 IP
            server_ppp_ip = connection.peer_ip
            client_ip = connection.local_ip

            # 1. 配置策略路由：让来自 server_ppp_ip 的流量通过 client_ip 出去
            routing_service = RoutingService()
            routing_service.setup_source_routing(
                interface=connection.interface,
                table_id=routing_table.table_id,
                table_name=routing_table.table_name,
                local_ip=server_ppp_ip,
                peer_ip=client_ip
            )

            # 2. 启动 Gost，绑定到服务器 PPP IP
            gost_service = GostService()
            pid = gost_service.start(
                port=proxy.listen_port,
                bind_ip=server_ppp_ip,
                interface=connection.interface
            )

            proxy.gost_pid = pid
            proxy.is_running = True
            proxy.save()

            # 3. 检测出口 IP（延迟执行以确保代理已就绪）
            import time
            exit_ip = None
            for attempt in range(3):
                time.sleep(2)
                exit_ip = IPDetectService.get_exit_ip_via_proxy(proxy.listen_port)
                if exit_ip:
                    proxy.exit_ip = exit_ip
                    proxy.save(update_fields=['exit_ip'])
                    break

            return Response({
                'message': '代理启动成功',
                'pid': pid,
                'port': proxy.listen_port,
                'bind_ip': server_ppp_ip,
                'exit_ip': exit_ip,
                'exit_via': client_ip
            })

        except Exception as e:
            SystemLog.log_error('proxy', f'启动代理失败: {e}', account=account)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止代理"""
        proxy = self.get_object()
        account = proxy.account

        if not proxy.is_running:
            return Response({'error': '代理未在运行'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 停止 Gost
            gost_service = GostService()
            gost_service.stop(proxy.listen_port)

            # 2. 清理策略路由
            try:
                routing_table = account.routing_table
                connection = account.current_connection
                if connection:
                    routing_service = RoutingService()
                    routing_service.cleanup_source_routing(
                        table_id=routing_table.table_id,
                        table_name=routing_table.table_name,
                        local_ip=connection.peer_ip  # 服务器 PPP IP
                    )
            except Exception:
                pass  # 路由清理失败不影响停止操作

            proxy.gost_pid = None
            proxy.is_running = False
            proxy.exit_ip = None
            proxy.save()

            return Response({'message': '代理停止成功'})

        except Exception as e:
            SystemLog.log_error('proxy', f'停止代理失败: {e}', account=account)
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
            routing_table = account.routing_table

            server_ppp_ip = connection.peer_ip
            client_ip = connection.local_ip

            # 1. 重新配置策略路由
            routing_service = RoutingService()
            routing_service.setup_source_routing(
                interface=connection.interface,
                table_id=routing_table.table_id,
                table_name=routing_table.table_name,
                local_ip=server_ppp_ip,
                peer_ip=client_ip
            )

            # 2. 重启 Gost
            gost_service = GostService()
            pid = gost_service.restart(
                port=proxy.listen_port,
                bind_ip=server_ppp_ip,
                interface=connection.interface
            )

            proxy.gost_pid = pid
            proxy.is_running = True
            proxy.save()

            # 3. 检测出口 IP
            import time
            exit_ip = None
            for attempt in range(3):
                time.sleep(2)
                exit_ip = IPDetectService.get_exit_ip_via_proxy(proxy.listen_port)
                if exit_ip:
                    proxy.exit_ip = exit_ip
                    proxy.save(update_fields=['exit_ip'])
                    break

            return Response({
                'message': '代理重启成功',
                'pid': pid,
                'bind_ip': server_ppp_ip,
                'exit_ip': exit_ip,
                'exit_via': client_ip
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
        import time
        gost_service = GostService()
        routing_service = RoutingService()
        started = 0
        failed = 0
        started_proxies = []

        for proxy in ProxyConfig.objects.filter(is_running=False, auto_start=True):
            account = proxy.account
            if not account.is_online:
                continue

            try:
                connection = account.current_connection
                routing_table = account.routing_table
                server_ppp_ip = connection.peer_ip
                client_ip = connection.local_ip

                # 配置策略路由
                routing_service.setup_source_routing(
                    interface=connection.interface,
                    table_id=routing_table.table_id,
                    table_name=routing_table.table_name,
                    local_ip=server_ppp_ip,
                    peer_ip=client_ip
                )

                # 启动 Gost
                pid = gost_service.start(
                    port=proxy.listen_port,
                    bind_ip=server_ppp_ip,
                    interface=connection.interface
                )
                proxy.gost_pid = pid
                proxy.is_running = True
                proxy.save()
                started += 1
                started_proxies.append(proxy)
            except Exception:
                failed += 1

        # 等待代理就绪后检测出口 IP
        if started_proxies:
            time.sleep(3)
            for proxy in started_proxies:
                try:
                    exit_ip = IPDetectService.get_exit_ip_via_proxy(proxy.listen_port)
                    if exit_ip:
                        proxy.exit_ip = exit_ip
                        proxy.save(update_fields=['exit_ip'])
                except Exception:
                    pass

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

    @action(detail=False, methods=['post'])
    def refresh_exit_ips(self, request):
        """刷新所有运行中代理的出口 IP"""
        updated = 0
        failed = 0

        for proxy in ProxyConfig.objects.filter(is_running=True):
            try:
                exit_ip = IPDetectService.get_exit_ip_via_proxy(proxy.listen_port)
                if exit_ip:
                    proxy.exit_ip = exit_ip
                    proxy.save(update_fields=['exit_ip'])
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return Response({'updated': updated, 'failed': failed})


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


class ServerConfigView(APIView):
    """服务器配置接口（单例）"""

    def _auto_detect_ips(self, config: ServerConfig) -> bool:
        """自动检测并更新 IP 地址，返回是否有更新"""
        ips = IPDetectService.detect_all()
        updated = False

        if ips['public_ip'] and ips['public_ip'] != config.public_ip:
            config.public_ip = ips['public_ip']
            updated = True

        if ips['private_ip'] and ips['private_ip'] != config.private_ip:
            config.private_ip = ips['private_ip']
            updated = True

        if updated:
            config.save()

        return updated

    def get(self, request):
        """获取服务器配置（自动检测 IP）"""
        config = ServerConfig.get_instance()
        # 自动检测 IP
        self._auto_detect_ips(config)
        serializer = ServerConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        """更新服务器配置（仅允许修改域名）"""
        config = ServerConfig.get_instance()
        # 只允许更新 domain 字段
        update_data = {}
        if 'domain' in request.data:
            update_data['domain'] = request.data['domain']

        serializer = ServerConfigSerializer(config, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """手动刷新 IP 地址"""
        config = ServerConfig.get_instance()
        ips = IPDetectService.detect_all()

        config.public_ip = ips['public_ip']
        config.private_ip = ips['private_ip']
        config.save()

        serializer = ServerConfigSerializer(config)
        return Response(serializer.data)
