"""连接状态模型"""

from django.db import models


class Connection(models.Model):
    """PPP 连接状态模型"""

    class Meta:
        db_table = 'connections'
        ordering = ['-connected_at']
        verbose_name = '连接'
        verbose_name_plural = '连接'

    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
    ]

    account = models.ForeignKey(
        'accounts.L2TPAccount',
        on_delete=models.CASCADE,
        related_name='connections',
        verbose_name='关联账号'
    )
    interface = models.CharField('接口名', max_length=16)
    peer_ip = models.GenericIPAddressField('对端IP')
    local_ip = models.GenericIPAddressField('本地IP')
    status = models.CharField('状态', max_length=16, choices=STATUS_CHOICES, default='online')
    connected_at = models.DateTimeField('连接时间', auto_now_add=True)
    disconnected_at = models.DateTimeField('断开时间', null=True, blank=True)
    bytes_sent = models.BigIntegerField('发送字节', default=0)
    bytes_received = models.BigIntegerField('接收字节', default=0)

    def __str__(self):
        return f'{self.interface} - {self.account.username} ({self.status})'

    @property
    def duration(self):
        """连接时长（秒）"""
        from django.utils import timezone

        if self.disconnected_at:
            return (self.disconnected_at - self.connected_at).total_seconds()
        return (timezone.now() - self.connected_at).total_seconds()

    @classmethod
    def get_online_connections(cls):
        """获取所有在线连接"""
        return cls.objects.filter(status='online').select_related('account')

    @classmethod
    def get_by_interface(cls, interface):
        """通过接口名获取在线连接"""
        return cls.objects.filter(interface=interface, status='online').first()

    @classmethod
    def get_by_ip(cls, ip):
        """通过 IP 获取在线连接"""
        return cls.objects.filter(local_ip=ip, status='online').first()
