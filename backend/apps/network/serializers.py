"""网络配置序列化器"""

from rest_framework import serializers

from .models import ProxyConfig, RoutingTable, ServerConfig


class ProxyConfigSerializer(serializers.ModelSerializer):
    """代理配置序列化器"""

    username = serializers.CharField(source='account.username', read_only=True)
    assigned_ip = serializers.CharField(source='account.assigned_ip', read_only=True)
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = ProxyConfig
        fields = [
            'id', 'account', 'username', 'assigned_ip', 'listen_port',
            'is_running', 'gost_pid', 'exit_ip', 'auto_start', 'is_online',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'gost_pid', 'exit_ip', 'is_running', 'created_at', 'updated_at']

    def get_is_online(self, obj):
        return obj.account.is_online


class ProxyConfigCreateSerializer(serializers.ModelSerializer):
    """代理配置创建序列化器"""

    class Meta:
        model = ProxyConfig
        fields = ['account', 'listen_port', 'auto_start']

    def validate_listen_port(self, value):
        from django.conf import settings

        if value < settings.PROXY_PORT_START or value > settings.PROXY_PORT_END:
            raise serializers.ValidationError(
                f'端口必须在 {settings.PROXY_PORT_START}-{settings.PROXY_PORT_END} 范围内'
            )
        return value


class RoutingTableSerializer(serializers.ModelSerializer):
    """路由表序列化器"""

    username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = RoutingTable
        fields = [
            'id', 'account', 'username', 'table_id', 'table_name',
            'interface', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardStatsSerializer(serializers.Serializer):
    """看板统计序列化器"""

    accounts_total = serializers.IntegerField()
    accounts_active = serializers.IntegerField()
    connections_online = serializers.IntegerField()
    proxies_running = serializers.IntegerField()


class ServerConfigSerializer(serializers.ModelSerializer):
    """服务器配置序列化器"""

    server_address = serializers.SerializerMethodField()

    class Meta:
        model = ServerConfig
        fields = ['domain', 'public_ip', 'private_ip', 'server_address', 'updated_at']

    def get_server_address(self, obj):
        return obj.get_server_address()
