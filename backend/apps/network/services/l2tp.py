"""L2TP 服务管理"""

import logging
import subprocess
from pathlib import Path

from apps.logs.models import SystemLog

logger = logging.getLogger(__name__)


class L2TPError(Exception):
    """L2TP 服务异常"""
    pass


class L2TPService:
    """L2TP 服务管理"""

    CHAP_SECRETS_PATH = '/etc/ppp/chap-secrets'
    XL2TPD_CONF_PATH = '/etc/xl2tpd/xl2tpd.conf'
    PPP_OPTIONS_PATH = '/etc/ppp/options.xl2tpd'

    def __init__(self):
        pass

    def _run_cmd(self, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        """执行命令"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f'命令执行失败: {" ".join(cmd)}, 错误: {e.stderr}')
            raise L2TPError(f'命令执行失败: {e.stderr}')

    def add_user(self, username: str, password: str, assigned_ip: str) -> bool:
        """添加 L2TP 用户到 chap-secrets

        Args:
            username: 用户名
            password: 密码
            assigned_ip: 分配的 IP 地址

        Returns:
            是否添加成功
        """
        chap_secrets = Path(self.CHAP_SECRETS_PATH)

        try:
            # 读取现有内容
            existing_lines = []
            if chap_secrets.exists():
                with open(chap_secrets) as f:
                    existing_lines = f.readlines()

            # 检查用户是否已存在
            for line in existing_lines:
                if line.strip() and not line.startswith('#'):
                    parts = line.split()
                    if parts and parts[0] == username:
                        logger.warning(f'用户 {username} 已存在于 chap-secrets')
                        return self.update_user(username, password, assigned_ip)

            # 添加新用户
            with open(chap_secrets, 'a') as f:
                f.write(f'{username}\t*\t{password}\t{assigned_ip}\n')

            logger.info(f'添加 L2TP 用户: {username} -> {assigned_ip}')
            SystemLog.log('l2tp', f'添加用户: {username}', details={'ip': assigned_ip})
            return True

        except IOError as e:
            logger.error(f'添加用户失败: {e}')
            SystemLog.log_error('l2tp', f'添加用户失败: {e}')
            raise L2TPError(f'添加用户失败: {e}')

    def update_user(self, username: str, password: str, assigned_ip: str) -> bool:
        """更新 L2TP 用户

        Args:
            username: 用户名
            password: 新密码
            assigned_ip: 新分配的 IP 地址

        Returns:
            是否更新成功
        """
        chap_secrets = Path(self.CHAP_SECRETS_PATH)

        try:
            lines = []
            found = False

            if chap_secrets.exists():
                with open(chap_secrets) as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            parts = line.split()
                            if parts and parts[0] == username:
                                lines.append(f'{username}\t*\t{password}\t{assigned_ip}\n')
                                found = True
                                continue
                        lines.append(line)

            if not found:
                lines.append(f'{username}\t*\t{password}\t{assigned_ip}\n')

            with open(chap_secrets, 'w') as f:
                f.writelines(lines)

            logger.info(f'更新 L2TP 用户: {username}')
            SystemLog.log('l2tp', f'更新用户: {username}', details={'ip': assigned_ip})
            return True

        except IOError as e:
            logger.error(f'更新用户失败: {e}')
            raise L2TPError(f'更新用户失败: {e}')

    def remove_user(self, username: str) -> bool:
        """删除 L2TP 用户

        Args:
            username: 用户名

        Returns:
            是否删除成功
        """
        chap_secrets = Path(self.CHAP_SECRETS_PATH)

        try:
            lines = []

            if chap_secrets.exists():
                with open(chap_secrets) as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            parts = line.split()
                            if parts and parts[0] == username:
                                continue
                        lines.append(line)

            with open(chap_secrets, 'w') as f:
                f.writelines(lines)

            logger.info(f'删除 L2TP 用户: {username}')
            SystemLog.log('l2tp', f'删除用户: {username}')
            return True

        except IOError as e:
            logger.error(f'删除用户失败: {e}')
            raise L2TPError(f'删除用户失败: {e}')

    def get_users(self) -> list:
        """获取所有 L2TP 用户

        Returns:
            用户列表 [{'username': str, 'ip': str}, ...]
        """
        chap_secrets = Path(self.CHAP_SECRETS_PATH)
        users = []

        try:
            if chap_secrets.exists():
                with open(chap_secrets) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 4:
                                users.append({
                                    'username': parts[0],
                                    'ip': parts[3]
                                })
        except IOError:
            pass

        return users

    def restart_service(self) -> bool:
        """重启 xl2tpd 服务"""
        try:
            self._run_cmd(['systemctl', 'restart', 'xl2tpd'])
            logger.info('xl2tpd 服务已重启')
            SystemLog.log('l2tp', 'xl2tpd 服务重启')
            return True
        except L2TPError:
            return False

    def reload_service(self) -> bool:
        """重载 xl2tpd 服务"""
        try:
            self._run_cmd(['systemctl', 'reload', 'xl2tpd'], check=False)
            logger.info('xl2tpd 服务已重载')
            return True
        except L2TPError:
            return False

    def get_service_status(self) -> dict:
        """获取 xl2tpd 服务状态"""
        try:
            result = self._run_cmd(['systemctl', 'is-active', 'xl2tpd'], check=False)
            active = result.stdout.strip() == 'active'

            result = self._run_cmd(['systemctl', 'is-enabled', 'xl2tpd'], check=False)
            enabled = result.stdout.strip() == 'enabled'

            return {
                'active': active,
                'enabled': enabled
            }
        except Exception:
            return {'active': False, 'enabled': False}

    def generate_xl2tpd_config(self, local_ip: str, ip_range_start: str, ip_range_end: str) -> str:
        """生成 xl2tpd 配置文件内容"""
        return f"""[global]
listen-addr = 0.0.0.0
port = 1701
ipsec saref = no

[lns default]
ip range = {ip_range_start}-{ip_range_end}
local ip = {local_ip}
require chap = yes
refuse pap = yes
require authentication = yes
name = l2tp-server
pppoptfile = {self.PPP_OPTIONS_PATH}
length bit = yes
"""

    def generate_ppp_options(self) -> str:
        """生成 PPP 配置文件内容"""
        return """ipcp-accept-local
ipcp-accept-remote
ms-dns 8.8.8.8
ms-dns 8.8.4.4
noccp
auth
mtu 1280
mru 1280
nodefaultroute
debug
lock
proxyarp
connect-delay 5000
"""
