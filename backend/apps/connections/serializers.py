"""连接状态序列化器"""

from rest_framework import serializers

from .models import Connection


class ConnectionSerializer(serializers.ModelSerializer):
    """连接序列化器"""

    username = serializers.CharField(source='account.username', read_only=True)
    assigned_ip = serializers.CharField(source='account.assigned_ip', read_only=True)
    duration = serializers.ReadOnlyField()

    class Meta:
        model = Connection
        fields = [
            'id', 'account', 'username', 'assigned_ip', 'interface',
            'peer_ip', 'local_ip', 'status', 'duration',
            'bytes_sent', 'bytes_received',
            'connected_at', 'disconnected_at'
        ]


class ConnectionOnlineSerializer(serializers.Serializer):
    """Client 上线回调序列化器"""

    interface = serializers.CharField(max_length=16)
    local_ip = serializers.IPAddressField()
    remote_ip = serializers.IPAddressField(required=False)
    peer_ip = serializers.IPAddressField(required=False)

    def validate(self, attrs):
        # remote_ip 和 peer_ip 是同一个意思，兼容不同参数名
        if not attrs.get('peer_ip') and attrs.get('remote_ip'):
            attrs['peer_ip'] = attrs.pop('remote_ip')
        return attrs


class ConnectionOfflineSerializer(serializers.Serializer):
    """Client 下线回调序列化器"""

    interface = serializers.CharField(max_length=16)


class AccountConnectionSummarySerializer(serializers.Serializer):
    """账号连接汇总序列化器 - 每个账号显示一条记录"""

    account_id = serializers.IntegerField()
    username = serializers.CharField()
    assigned_ip = serializers.CharField()
    interface = serializers.CharField(allow_blank=True)
    peer_ip = serializers.CharField(allow_blank=True)
    local_ip = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    duration = serializers.FloatField()
    connected_at = serializers.DateTimeField(allow_null=True)
    disconnected_at = serializers.DateTimeField(allow_null=True)
    total_bytes_sent = serializers.IntegerField()
    total_bytes_received = serializers.IntegerField()
    connection_count = serializers.IntegerField()
