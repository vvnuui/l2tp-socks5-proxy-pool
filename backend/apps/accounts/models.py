"""L2TP 账号模型"""

import re

from django.conf import settings
from django.db import models


class L2TPAccount(models.Model):
    """L2TP 用户账号模型"""

    class Meta:
        db_table = 'l2tp_accounts'
        ordering = ['-created_at']
        verbose_name = 'L2TP账号'
        verbose_name_plural = 'L2TP账号'

    username = models.CharField('用户名', max_length=64, unique=True)
    password = models.CharField('密码', max_length=128)
    assigned_ip = models.GenericIPAddressField('分配IP', unique=True)
    is_active = models.BooleanField('启用状态', default=True)
    remark = models.CharField('备注', max_length=255, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        return f'{self.username} ({self.assigned_ip})'

    def clean(self):
        from django.core.exceptions import ValidationError

        if not re.match(r'^[a-zA-Z0-9_]+$', self.username):
            raise ValidationError({'username': '用户名只能包含字母、数字和下划线'})

    @property
    def is_online(self):
        """检查账号是否在线"""
        return hasattr(self, 'current_connection') and self.current_connection is not None

    @property
    def current_connection(self):
        """获取当前连接"""
        return self.connections.filter(status='online').first()

    @property
    def proxy_config(self):
        """获取代理配置"""
        try:
            return self.proxyconfig
        except L2TPAccount.proxyconfig.RelatedObjectDoesNotExist:
            return None

    @classmethod
    def get_next_available_ip(cls):
        """获取下一个可用的 IP 地址"""
        import ipaddress

        start_ip = ipaddress.ip_address(settings.PROXY_IP_POOL_START)
        end_ip = ipaddress.ip_address(settings.PROXY_IP_POOL_END)

        used_ips = set(cls.objects.values_list('assigned_ip', flat=True))

        current_ip = start_ip
        while current_ip <= end_ip:
            ip_str = str(current_ip)
            if ip_str not in used_ips:
                return ip_str
            current_ip += 1

        return None
