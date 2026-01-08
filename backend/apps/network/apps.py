import sys
from django.apps import AppConfig


class NetworkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.network'
    verbose_name = '网络配置管理'
    _synced = False  # 防止重复执行

    def ready(self):
        """应用启动时同步代理状态"""
        # 排除 migrate、collectstatic 等命令
        if len(sys.argv) > 1 and sys.argv[1] in ('migrate', 'collectstatic', 'makemigrations', 'shell'):
            return

        if not NetworkConfig._synced:
            NetworkConfig._synced = True
            # 延迟执行，确保数据库连接就绪
            from django.db import connection
            try:
                connection.ensure_connection()
                self._sync_proxy_states()
            except Exception:
                pass

    def _sync_proxy_states(self):
        """同步代理状态与实际进程"""
        try:
            from .models import ProxyConfig
            from .services import GostService

            gost_service = GostService()
            updated_count = 0

            for proxy in ProxyConfig.objects.filter(is_running=True):
                status = gost_service.get_status(proxy.listen_port)
                if not status['running']:
                    proxy.is_running = False
                    proxy.gost_pid = None
                    proxy.exit_ip = None
                    proxy.save(update_fields=['is_running', 'gost_pid', 'exit_ip'])
                    updated_count += 1

            if updated_count > 0:
                from apps.logs.models import SystemLog
                SystemLog.log_info(
                    'system',
                    f'启动时同步代理状态：重置 {updated_count} 个已停止的代理'
                )
                print(f'[启动同步] 重置 {updated_count} 个已停止的代理')
        except Exception as e:
            print(f'同步代理状态失败: {e}')
