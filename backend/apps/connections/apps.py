from django.apps import AppConfig


class ConnectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.connections'
    verbose_name = '连接状态管理'
