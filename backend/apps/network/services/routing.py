"""策略路由管理服务"""

import logging
import subprocess
from pathlib import Path

from apps.logs.models import SystemLog

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """路由配置异常"""
    pass


class RoutingService:
    """策略路由管理服务"""

    RT_TABLES_PATH = '/etc/iproute2/rt_tables'

    def __init__(self):
        self._ensure_rt_tables()

    def _ensure_rt_tables(self):
        """确保 rt_tables 文件存在"""
        rt_tables = Path(self.RT_TABLES_PATH)
        if not rt_tables.exists():
            logger.warning(f'{self.RT_TABLES_PATH} 不存在')

    def _run_cmd(self, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f'命令执行失败: {" ".join(cmd)}, 错误: {e.stderr}')
            raise RoutingError(f'命令执行失败: {e.stderr}')

    def _table_exists(self, table_id: int) -> bool:
        """检查路由表是否存在"""
        try:
            with open(self.RT_TABLES_PATH) as f:
                for line in f:
                    if line.strip().startswith(str(table_id)):
                        return True
        except IOError:
            pass
        return False

    def create_routing_table(self, table_id: int, table_name: str) -> bool:
        """创建路由表

        Args:
            table_id: 路由表 ID (100-252)
            table_name: 路由表名称

        Returns:
            是否创建成功
        """
        if self._table_exists(table_id):
            logger.info(f'路由表 {table_name} (ID: {table_id}) 已存在')
            return True

        try:
            with open(self.RT_TABLES_PATH, 'a') as f:
                f.write(f'{table_id} {table_name}\n')

            logger.info(f'创建路由表: {table_name} (ID: {table_id})')
            SystemLog.log_routing(f'创建路由表: {table_name}', details={'table_id': table_id})
            return True

        except IOError as e:
            logger.error(f'创建路由表失败: {e}')
            SystemLog.log_error('routing', f'创建路由表失败: {e}')
            raise RoutingError(f'创建路由表失败: {e}')

    def setup_routing(self, interface: str, table_id: int, table_name: str, proxy_port: int) -> bool:
        """配置策略路由 (基于 fwmark，已废弃，推荐使用 setup_source_routing)

        Args:
            interface: PPP 接口名 (ppp0, ppp1, ...)
            table_id: 路由表 ID
            table_name: 路由表名称
            proxy_port: 代理监听端口

        Returns:
            是否配置成功
        """
        try:
            # 1. 创建路由表
            self.create_routing_table(table_id, table_name)

            # 2. 添加默认路由到路由表
            self._run_cmd(['ip', 'route', 'add', 'default', 'dev', interface, 'table', table_name], check=False)

            # 3. 添加路由策略 (基于 fwmark)
            self._run_cmd(
                ['ip', 'rule', 'add', 'fwmark', str(table_id), 'table', table_name, 'priority', '100'],
                check=False
            )

            # 4. 配置 iptables 打标签
            self._run_cmd([
                'iptables', '-t', 'mangle', '-A', 'OUTPUT',
                '-p', 'tcp', '--sport', str(proxy_port),
                '-j', 'MARK', '--set-mark', str(table_id)
            ], check=False)

            logger.info(f'策略路由配置完成: {interface} -> {table_name}')
            SystemLog.log_routing(
                f'策略路由配置完成: {interface}',
                interface=interface,
                details={'table_id': table_id, 'proxy_port': proxy_port}
            )
            return True

        except RoutingError:
            return False

    def setup_source_routing(self, interface: str, table_id: int, table_name: str,
                             local_ip: str, peer_ip: str) -> bool:
        """配置基于源 IP 的策略路由

        让来自 local_ip 的流量通过 peer_ip (L2TP 客户端) 转发出去

        Args:
            interface: PPP 接口名 (ppp0, ppp1, ...)
            table_id: 路由表 ID
            table_name: 路由表名称
            local_ip: 本地 PPP IP (服务器端，如 10.0.0.1)
            peer_ip: 对端 IP (客户端，如 10.0.0.2)

        Returns:
            是否配置成功
        """
        try:
            # 1. 创建路由表
            self.create_routing_table(table_id, table_name)

            # 2. 添加默认路由：通过 peer_ip 出去
            self._run_cmd([
                'ip', 'route', 'replace', 'default',
                'via', peer_ip, 'dev', interface, 'table', table_name
            ], check=False)

            # 3. 添加路由策略：来自 local_ip 的流量使用此路由表
            # 先删除可能存在的旧规则
            self._run_cmd(['ip', 'rule', 'del', 'from', local_ip, 'table', table_name], check=False)
            self._run_cmd([
                'ip', 'rule', 'add', 'from', local_ip, 'table', table_name, 'priority', '100'
            ], check=True)

            logger.info(f'源路由配置完成: {local_ip} -> {peer_ip} via {interface}')
            SystemLog.log_routing(
                f'源路由配置完成: {interface}',
                interface=interface,
                details={'table_id': table_id, 'local_ip': local_ip, 'peer_ip': peer_ip}
            )
            return True

        except RoutingError as e:
            logger.error(f'源路由配置失败: {e}')
            return False

    def cleanup_source_routing(self, table_id: int, table_name: str, local_ip: str) -> bool:
        """清理基于源 IP 的策略路由

        Args:
            table_id: 路由表 ID
            table_name: 路由表名称
            local_ip: 本地 PPP IP

        Returns:
            是否清理成功
        """
        try:
            # 1. 删除路由策略
            self._run_cmd(['ip', 'rule', 'del', 'from', local_ip, 'table', table_name], check=False)

            # 2. 删除路由
            self._run_cmd(['ip', 'route', 'del', 'default', 'table', table_name], check=False)

            logger.info(f'源路由清理完成: {local_ip}, table={table_name}')
            SystemLog.log_routing(f'源路由清理完成: table={table_name}')
            return True

        except Exception as e:
            logger.error(f'清理源路由失败: {e}')
            return False

    def cleanup_routing(self, interface: str, table_id: int, table_name: str, proxy_port: int) -> bool:
        """清理策略路由

        Args:
            interface: PPP 接口名
            table_id: 路由表 ID
            table_name: 路由表名称
            proxy_port: 代理监听端口

        Returns:
            是否清理成功
        """
        try:
            # 1. 删除 iptables 规则
            self._run_cmd([
                'iptables', '-t', 'mangle', '-D', 'OUTPUT',
                '-p', 'tcp', '--sport', str(proxy_port),
                '-j', 'MARK', '--set-mark', str(table_id)
            ], check=False)

            # 2. 删除路由策略
            self._run_cmd(
                ['ip', 'rule', 'del', 'fwmark', str(table_id), 'table', table_name],
                check=False
            )

            # 3. 删除路由
            self._run_cmd(['ip', 'route', 'del', 'default', 'table', table_name], check=False)

            logger.info(f'策略路由清理完成: {interface}')
            SystemLog.log_routing(f'策略路由清理完成: {interface}', interface=interface)
            return True

        except Exception as e:
            logger.error(f'清理路由失败: {e}')
            return False

    def get_interface_info(self, interface: str) -> dict | None:
        """获取接口信息"""
        try:
            result = self._run_cmd(['ip', 'addr', 'show', interface], check=False)
            if result.returncode != 0:
                return None

            info = {'interface': interface, 'up': False, 'ip': None}

            for line in result.stdout.split('\n'):
                if 'state UP' in line:
                    info['up'] = True
                if 'inet ' in line:
                    parts = line.strip().split()
                    info['ip'] = parts[1].split('/')[0]

            return info
        except Exception:
            return None

    def list_ppp_interfaces(self) -> list:
        """列出所有 PPP 接口"""
        result = self._run_cmd(['ip', 'link', 'show', 'type', 'ppp'], check=False)
        interfaces = []

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ': ppp' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        name = parts[1].strip().split('@')[0]
                        interfaces.append(name)

        return interfaces
