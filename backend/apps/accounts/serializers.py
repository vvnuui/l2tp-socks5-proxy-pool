"""L2TP 账号序列化器"""

import re

from rest_framework import serializers

from .models import L2TPAccount


class L2TPAccountSerializer(serializers.ModelSerializer):
    """L2TP 账号序列化器"""

    is_online = serializers.ReadOnlyField()
    current_interface = serializers.SerializerMethodField()
    proxy_port = serializers.SerializerMethodField()
    proxy_running = serializers.SerializerMethodField()

    class Meta:
        model = L2TPAccount
        fields = [
            'id', 'username', 'password', 'assigned_ip', 'is_active', 'remark',
            'is_online', 'current_interface', 'proxy_port', 'proxy_running',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_current_interface(self, obj):
        conn = obj.current_connection
        return conn.interface if conn else None

    def get_proxy_port(self, obj):
        config = obj.proxy_config
        return config.listen_port if config else None

    def get_proxy_running(self, obj):
        config = obj.proxy_config
        return config.is_running if config else False

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError('用户名只能包含字母、数字和下划线')
        return value

    def validate_assigned_ip(self, value):
        import ipaddress
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise serializers.ValidationError('无效的 IP 地址')
        return value


class L2TPAccountCreateSerializer(serializers.ModelSerializer):
    """L2TP 账号创建序列化器"""

    auto_assign_ip = serializers.BooleanField(default=True, write_only=True)
    auto_create_proxy = serializers.BooleanField(default=True, write_only=True)

    class Meta:
        model = L2TPAccount
        fields = ['username', 'password', 'assigned_ip', 'is_active', 'remark',
                  'auto_assign_ip', 'auto_create_proxy']

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError('用户名只能包含字母、数字和下划线')
        return value

    def validate(self, attrs):
        auto_assign_ip = attrs.pop('auto_assign_ip', True)

        if auto_assign_ip and not attrs.get('assigned_ip'):
            next_ip = L2TPAccount.get_next_available_ip()
            if not next_ip:
                raise serializers.ValidationError({'assigned_ip': 'IP 地址池已耗尽'})
            attrs['assigned_ip'] = next_ip

        return attrs

    def create(self, validated_data):
        auto_create_proxy = validated_data.pop('auto_create_proxy', True)
        account = super().create(validated_data)

        if auto_create_proxy:
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

        return account


class L2TPAccountListSerializer(serializers.ModelSerializer):
    """L2TP 账号列表序列化器（简化版）"""

    is_online = serializers.ReadOnlyField()
    proxy_port = serializers.SerializerMethodField()

    class Meta:
        model = L2TPAccount
        fields = ['id', 'username', 'assigned_ip', 'is_active', 'is_online',
                  'proxy_port', 'created_at']

    def get_proxy_port(self, obj):
        config = obj.proxy_config
        return config.listen_port if config else None
