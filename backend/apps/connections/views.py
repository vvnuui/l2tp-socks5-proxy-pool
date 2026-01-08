"""连接状态视图"""

from django.conf import settings
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Sum, Count, Max

from apps.accounts.models import L2TPAccount
from apps.logs.models import SystemLog
from apps.network.models import ProxyConfig, RoutingTable
from apps.network.services import GostService, RoutingService

from .models import Connection
from .serializers import AccountConnectionSummarySerializer, ConnectionSerializer


class ConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """连接状态查看接口"""

    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'interface']
    ordering_fields = ['connected_at', 'disconnected_at']
    ordering = ['-connected_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        online_only = self.request.query_params.get('online_only', 'false')
        if online_only.lower() == 'true':
            queryset = queryset.filter(status='online')
        return queryset.select_related('account')

    @action(detail=False, methods=['get'])
    def online(self, request):
        """获取所有在线连接"""
        connections = Connection.get_online_connections()
        serializer = self.get_serializer(connections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取连接统计"""
        total = Connection.objects.count()
        online = Connection.objects.filter(status='online').count()

        return Response({
            'total': total,
            'online': online,
            'offline': total - online
        })

    @action(detail=False, methods=['get'])
    def by_account(self, request):
        """按账号汇总连接信息 - 每个账号仅显示一条记录"""
        # 获取筛选参数
        status_filter = request.query_params.get('status', '')

        # 获取所有账号
        accounts = L2TPAccount.objects.all()

        result = []
        for account in accounts:
            # 获取该账号的所有连接
            connections = Connection.objects.filter(account=account)

            # 计算总流量
            traffic = connections.aggregate(
                total_sent=Sum('bytes_sent'),
                total_received=Sum('bytes_received'),
                count=Count('id')
            )

            # 获取当前/最新连接
            current_conn = connections.filter(status='online').first()
            if not current_conn:
                current_conn = connections.order_by('-connected_at').first()

            # 确定状态
            is_online = connections.filter(status='online').exists()
            conn_status = 'online' if is_online else 'offline'

            # 应用状态筛选
            if status_filter and conn_status != status_filter:
                continue

            # 构建汇总数据
            summary = {
                'account_id': account.id,
                'username': account.username,
                'assigned_ip': account.assigned_ip,
                'interface': current_conn.interface if current_conn else '',
                'peer_ip': current_conn.peer_ip if current_conn else '',
                'local_ip': current_conn.local_ip if current_conn else '',
                'status': conn_status,
                'duration': current_conn.duration if current_conn else 0,
                'connected_at': current_conn.connected_at if current_conn else None,
                'disconnected_at': current_conn.disconnected_at if current_conn else None,
                'total_bytes_sent': traffic['total_sent'] or 0,
                'total_bytes_received': traffic['total_received'] or 0,
                'connection_count': traffic['count'] or 0,
            }
            result.append(summary)

        # 按状态和用户名排序（在线的排前面）
        result.sort(key=lambda x: (0 if x['status'] == 'online' else 1, x['username']))

        serializer = AccountConnectionSummarySerializer(result, many=True)
        return Response({
            'count': len(result),
            'results': serializer.data
        })


class PPPCallbackView(APIView):
    """PPP 钩子统一回调接口"""

    permission_classes = [AllowAny]

    def _verify_token(self, request):
        """验证 Token"""
        # 支持多种 header 格式
        token = request.headers.get('X-PPP-Token', '')
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Token '):
                token = auth_header[6:]
        return token == settings.PPP_HOOK_TOKEN

    def post(self, request):
        """处理 PPP 回调"""
        if not self._verify_token(request):
            return Response({'error': '认证失败'}, status=status.HTTP_401_UNAUTHORIZED)

        action = request.data.get('action')
        if action == 'up':
            return self._handle_online(request)
        elif action == 'down':
            return self._handle_offline(request)
        else:
            return Response({'error': '无效的 action'}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_online(self, request):
        """处理 Client 上线"""
        interface = request.data.get('interface')
        local_ip = request.data.get('local_ip')
        peer_ip = request.data.get('peer_ip', '0.0.0.0')
        username = request.data.get('username', '')

        if not interface or not local_ip:
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找账号（优先通过 IP，其次通过用户名）
        account = None
        try:
            account = L2TPAccount.objects.get(assigned_ip=local_ip)
        except L2TPAccount.DoesNotExist:
            if username:
                try:
                    account = L2TPAccount.objects.get(username=username)
                except L2TPAccount.DoesNotExist:
                    pass

        if not account:
            SystemLog.log_error('connection', f'未知连接上线: IP={local_ip}, user={username}',
                              details={'interface': interface})
            return Response({'error': '未找到对应的账号'}, status=status.HTTP_404_NOT_FOUND)

        # 关闭之前的连接
        Connection.objects.filter(account=account, status='online').update(
            status='offline',
            disconnected_at=timezone.now()
        )

        # 创建新连接记录
        connection = Connection.objects.create(
            account=account,
            interface=interface,
            peer_ip=peer_ip,
            local_ip=local_ip,
            status='online'
        )

        # 更新路由表和启动代理
        # IP 说明:
        # peer_ip = 服务器 PPP IP (如 10.0.0.1)，Gost 绑定此 IP
        # local_ip = 客户端分配的 IP (如 10.0.0.2)，流量路由到此 IP
        server_ppp_ip = peer_ip
        client_ip = local_ip

        try:
            routing_table = account.routing_table
            routing_table.interface = interface
            routing_table.is_active = True
            routing_table.save()

            routing_service = RoutingService()
            proxy_config = account.proxy_config

            if proxy_config:
                # 配置基于源 IP 的策略路由
                routing_service.setup_source_routing(
                    interface=interface,
                    table_id=routing_table.table_id,
                    table_name=routing_table.table_name,
                    local_ip=server_ppp_ip,
                    peer_ip=client_ip
                )

                # 自动启动代理
                if proxy_config.auto_start:
                    gost_service = GostService()
                    try:
                        pid = gost_service.start(
                            port=proxy_config.listen_port,
                            bind_ip=server_ppp_ip,
                            interface=interface
                        )
                        proxy_config.gost_pid = pid
                        proxy_config.is_running = True
                        proxy_config.save()
                    except Exception as e:
                        SystemLog.log_error('proxy', f'自动启动代理失败: {e}', account=account)
        except Exception as e:
            SystemLog.log_error('routing', f'配置路由失败: {e}', account=account)

        SystemLog.log_connection(
            f'Client 上线: {account.username}',
            account=account,
            interface=interface,
            details={'local_ip': local_ip, 'peer_ip': peer_ip}
        )

        return Response({
            'message': 'OK',
            'connection_id': connection.id,
            'account_id': account.id
        })

    def _handle_offline(self, request):
        """处理 Client 下线"""
        interface = request.data.get('interface')
        local_ip = request.data.get('local_ip', '')

        if not interface:
            return Response({'error': '缺少 interface 参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找连接
        connection = Connection.get_by_interface(interface)
        if not connection and local_ip:
            connection = Connection.get_by_ip(local_ip)

        if not connection:
            return Response({'error': '未找到连接'}, status=status.HTTP_404_NOT_FOUND)

        account = connection.account

        # 停止代理（容器内可能不可用）
        try:
            if account.proxy_config and account.proxy_config.is_running:
                gost_service = GostService()
                gost_service.stop(account.proxy_config.listen_port)
                account.proxy_config.is_running = False
                account.proxy_config.gost_pid = None
                account.proxy_config.save()
        except Exception:
            pass

        # 清理路由（容器内可能不可用）
        try:
            routing_table = account.routing_table
            if routing_table.is_active:
                routing_service = RoutingService()
                routing_service.cleanup_routing(
                    interface=interface,
                    table_id=routing_table.table_id,
                    table_name=routing_table.table_name,
                    proxy_port=account.proxy_config.listen_port if account.proxy_config else 0
                )
                routing_table.interface = ''
                routing_table.is_active = False
                routing_table.save()
        except Exception as e:
            SystemLog.log_error('routing', f'清理路由失败: {e}', account=account)

        # 更新连接状态
        connection.status = 'offline'
        connection.disconnected_at = timezone.now()
        connection.save()

        SystemLog.log_connection(
            f'Client 下线: {account.username}',
            account=account,
            interface=interface
        )

        return Response({'message': 'OK'})
