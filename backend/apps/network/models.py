"""网络配置模型"""

from django.conf import settings
from django.db import models


class ServerConfig(models.Model):
    """服务器配置（单例模型）"""

    class Meta:
        db_table = 'server_config'
        verbose_name = '服务器配置'
        verbose_name_plural = '服务器配置'

    domain = models.CharField('域名', max_length=255, blank=True, default='')
    public_ip = models.GenericIPAddressField('公网 IP', blank=True, null=True)
    private_ip = models.GenericIPAddressField('内网 IP', blank=True, null=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        return f'服务器配置: {self.get_server_address()}'

    def get_server_address(self):
        """获取服务器地址，优先级：域名 > 公网IP > 内网IP"""
        if self.domain:
            return self.domain
        if self.public_ip:
            return self.public_ip
        if self.private_ip:
            return self.private_ip
        return '服务器IP'

    @classmethod
    def get_instance(cls):
        """获取单例配置，不存在则创建"""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def save(self, *args, **kwargs):
        """确保只有一条记录"""
        self.pk = 1
        super().save(*args, **kwargs)


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
    exit_ip = models.GenericIPAddressField('出口IP', blank=True, null=True)
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
