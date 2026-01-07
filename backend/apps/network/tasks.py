"""网络配置 Celery 任务"""

from celery import shared_task

from apps.logs.models import SystemLog


@shared_task
def cleanup_stale_processes():
    """清理僵死的 Gost 进程"""
    from .models import ProxyConfig
    from .services import GostService

    gost_service = GostService()
    cleaned = gost_service.cleanup_stale()

    # 同步数据库状态
    for proxy in ProxyConfig.objects.filter(is_running=True):
        if not gost_service.is_running(proxy.listen_port):
            proxy.is_running = False
            proxy.gost_pid = None
            proxy.save()

    if cleaned > 0:
        SystemLog.log('system', f'清理了 {cleaned} 个僵死进程记录')

    return {'cleaned': cleaned}


@shared_task
def sync_proxy_status():
    """同步所有代理状态"""
    from .models import ProxyConfig
    from .services import GostService

    gost_service = GostService()
    synced = 0

    for proxy in ProxyConfig.objects.all():
        running = gost_service.is_running(proxy.listen_port)
        if running != proxy.is_running:
            proxy.is_running = running
            if not running:
                proxy.gost_pid = None
            proxy.save()
            synced += 1

    return {'synced': synced}


@shared_task
def auto_start_proxies():
    """自动启动代理（用于账号上线后）"""
    from apps.accounts.models import L2TPAccount

    from .models import ProxyConfig
    from .services import GostService

    gost_service = GostService()
    started = 0

    for proxy in ProxyConfig.objects.filter(is_running=False, auto_start=True):
        account = proxy.account
        if not account.is_online:
            continue

        try:
            connection = account.current_connection
            pid = gost_service.start(
                port=proxy.listen_port,
                bind_ip=account.assigned_ip,
                interface=connection.interface
            )
            proxy.gost_pid = pid
            proxy.is_running = True
            proxy.save()
            started += 1
        except Exception as e:
            SystemLog.log_error('proxy', f'自动启动代理失败: {e}', account=account)

    return {'started': started}


@shared_task
def check_connection_health():
    """检查连接健康状态"""
    from apps.connections.models import Connection

    from .services import RoutingService

    routing_service = RoutingService()
    ppp_interfaces = set(routing_service.list_ppp_interfaces())

    stale = 0
    for connection in Connection.objects.filter(status='online'):
        if connection.interface not in ppp_interfaces:
            from django.utils import timezone

            connection.status = 'offline'
            connection.disconnected_at = timezone.now()
            connection.save()
            stale += 1

            SystemLog.log_connection(
                f'检测到僵死连接: {connection.account.username}',
                account=connection.account,
                interface=connection.interface,
                level='warning'
            )

    return {'stale_connections': stale}
