"""系统日志模型"""

from django.db import models


class SystemLog(models.Model):
    """系统日志模型"""

    class Meta:
        db_table = 'system_logs'
        ordering = ['-created_at']
        verbose_name = '系统日志'
        verbose_name_plural = '系统日志'

    LEVEL_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
        ('debug', '调试'),
    ]

    TYPE_CHOICES = [
        ('connection', '连接'),
        ('proxy', '代理'),
        ('routing', '路由'),
        ('system', '系统'),
        ('l2tp', 'L2TP'),
    ]

    level = models.CharField('日志级别', max_length=16, choices=LEVEL_CHOICES, default='info')
    log_type = models.CharField('日志类型', max_length=16, choices=TYPE_CHOICES)
    message = models.TextField('日志消息')
    details = models.JSONField('详细信息', null=True, blank=True)
    account = models.ForeignKey(
        'accounts.L2TPAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name='关联账号'
    )
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    interface = models.CharField('接口名', max_length=16, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    def __str__(self):
        return f'[{self.level.upper()}] {self.log_type}: {self.message[:50]}'

    @classmethod
    def log(cls, log_type, message, level='info', account=None, ip_address=None, interface='', details=None):
        """创建日志记录"""
        return cls.objects.create(
            log_type=log_type,
            message=message,
            level=level,
            account=account,
            ip_address=ip_address,
            interface=interface,
            details=details
        )

    @classmethod
    def log_connection(cls, message, account=None, interface='', level='info', details=None):
        """记录连接日志"""
        return cls.log('connection', message, level, account, interface=interface, details=details)

    @classmethod
    def log_proxy(cls, message, account=None, level='info', details=None):
        """记录代理日志"""
        return cls.log('proxy', message, level, account, details=details)

    @classmethod
    def log_routing(cls, message, account=None, interface='', level='info', details=None):
        """记录路由日志"""
        return cls.log('routing', message, level, account, interface=interface, details=details)

    @classmethod
    def log_error(cls, log_type, message, account=None, details=None):
        """记录错误日志"""
        return cls.log(log_type, message, 'error', account, details=details)
