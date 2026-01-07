"""网络配置模型"""

from django.conf import settings
from django.db import models


class ProxyConfig(models.Model):
    """Socks5 代理配置模型"""

    class Meta:
        db_table = 'proxy_configs'
        ordering = ['listen_port']
        verbose_name = '代理配置'
        verbose_name_plural = '代理配置'

    account = models.OneToOneField(
        'accounts.L2TPAccount',
        on_delete=models.CASCADE,
        related_name='proxyconfig',
        verbose_name='关联账号'
    )
    listen_port = models.IntegerField('监听端口', unique=True)
    is_running = models.BooleanField('运行状态', default=False)
    gost_pid = models.IntegerField('Gost进程ID', null=True, blank=True)
    auto_start = models.BooleanField('自动启动', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        status = '运行中' if self.is_running else '已停止'
        return f':{self.listen_port} -> {self.account.assigned_ip} ({status})'

    @classmethod
    def get_next_available_port(cls):
        """获取下一个可用的端口"""
        start_port = settings.PROXY_PORT_START
        end_port = settings.PROXY_PORT_END

        used_ports = set(cls.objects.values_list('listen_port', flat=True))

        for port in range(start_port, end_port + 1):
            if port not in used_ports:
                return port

        return None

    @classmethod
    def get_running_proxies(cls):
        """获取所有运行中的代理"""
        return cls.objects.filter(is_running=True).select_related('account')


class RoutingTable(models.Model):
    """路由表配置模型"""

    class Meta:
        db_table = 'routing_tables'
        ordering = ['table_id']
        verbose_name = '路由表'
        verbose_name_plural = '路由表'

    account = models.OneToOneField(
        'accounts.L2TPAccount',
        on_delete=models.CASCADE,
        related_name='routing_table',
        verbose_name='关联账号'
    )
    table_id = models.IntegerField('路由表ID', unique=True)
    table_name = models.CharField('路由表名', max_length=32, unique=True)
    interface = models.CharField('绑定接口', max_length=16, blank=True, default='')
    is_active = models.BooleanField('是否激活', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        return f'{self.table_name} (ID: {self.table_id})'

    @classmethod
    def get_next_table_id(cls):
        """获取下一个可用的路由表 ID"""
        last = cls.objects.order_by('-table_id').first()
        if last:
            return last.table_id + 1
        return 100
