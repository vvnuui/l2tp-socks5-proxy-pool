"""系统日志序列化器"""

from rest_framework import serializers

from .models import SystemLog


class SystemLogSerializer(serializers.ModelSerializer):
    """系统日志序列化器"""

    username = serializers.SerializerMethodField()

    class Meta:
        model = SystemLog
        fields = [
            'id', 'level', 'log_type', 'message', 'details',
            'account', 'username', 'ip_address', 'interface',
            'created_at'
        ]

    def get_username(self, obj):
        return obj.account.username if obj.account else None
