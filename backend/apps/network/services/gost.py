"""Gost 代理服务管理"""

import logging
import os
import signal
import subprocess
from pathlib import Path

from django.conf import settings

from apps.logs.models import SystemLog

logger = logging.getLogger(__name__)


class GostError(Exception):
    """Gost 服务异常"""
    pass


class GostService:
    """Gost 代理服务管理"""

    def __init__(self):
        self.bin_path = settings.GOST_BIN_PATH
        self.log_dir = Path(settings.GOST_LOG_DIR)
        self.pid_dir = Path(settings.GOST_PID_DIR)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def _open_firewall_port(self, port: int) -> bool:
        """开放防火墙端口

        Args:
            port: 要开放的端口

        Returns:
            是否成功
        """
        try:
            # 检查规则是否已存在
            check_cmd = ['iptables', '-C', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT']
            result = subprocess.run(check_cmd, capture_output=True)

            if result.returncode == 0:
                logger.debug(f'防火墙端口 {port} 已开放')
                return True

            # 添加规则
            add_cmd = ['iptables', '-A', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT']
            subprocess.run(add_cmd, check=True, capture_output=True)
            logger.info(f'防火墙端口已开放: {port}')
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f'开放防火墙端口失败: {port}, 错误: {e}')
            return False
        except FileNotFoundError:
            logger.warning('iptables 命令不可用，跳过防火墙配置')
            return True

    def _close_firewall_port(self, port: int) -> bool:
        """关闭防火墙端口

        Args:
            port: 要关闭的端口

        Returns:
            是否成功
        """
        try:
            # 删除规则
            del_cmd = ['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT']
            subprocess.run(del_cmd, capture_output=True)  # 不检查返回值，规则可能不存在
            logger.info(f'防火墙端口已关闭: {port}')
            return True

        except FileNotFoundError:
            logger.warning('iptables 命令不可用，跳过防火墙配置')
            return True

    def _get_pid_file(self, port: int) -> Path:
        """获取 PID 文件路径"""
        return self.pid_dir / f'{port}.pid'

    def _get_log_file(self, port: int) -> Path:
        """获取日志文件路径"""
        return self.log_dir / f'{port}.log'

    def _read_pid(self, port: int) -> int | None:
        """读取 PID"""
        pid_file = self._get_pid_file(port)
        if pid_file.exists():
            try:
                return int(pid_file.read_text().strip())
            except (ValueError, IOError):
                return None
        return None

    def _write_pid(self, port: int, pid: int):
        """写入 PID"""
        self._get_pid_file(port).write_text(str(pid))

    def _remove_pid(self, port: int):
        """删除 PID 文件"""
        pid_file = self._get_pid_file(port)
        if pid_file.exists():
            pid_file.unlink()

    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否运行"""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def is_running(self, port: int) -> bool:
        """检查指定端口的代理是否运行"""
        pid = self._read_pid(port)
        if pid and self._is_process_running(pid):
            return True
        return False

    def start(self, port: int, bind_ip: str, interface: str = '') -> int:
        """启动 Socks5 代理 (Gost v3)

        Args:
            port: 监听端口
            bind_ip: 绑定出口 IP (保留参数，用于日志记录)
            interface: 绑定接口名 (必需，如 ppp0)，出站流量将通过此接口

        Returns:
            进程 PID

        Raises:
            GostError: 启动失败时
        """
        if self.is_running(port):
            raise GostError(f'端口 {port} 的代理已在运行')

        if not interface:
            raise GostError('必须指定绑定接口 (interface)')

        log_file = self._get_log_file(port)

        # 构建命令：Gost v3 使用 URL 参数 interface 绑定出站接口
        # 格式: gost -L socks5://:port?interface=ppp0
        cmd = [
            self.bin_path,
            '-L', f'socks5://:{port}?interface={interface}'
        ]

        try:
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

            self._write_pid(port, process.pid)

            # 开放防火墙端口
            self._open_firewall_port(port)

            logger.info(f'Gost 代理已启动: 端口={port}, 接口={interface}, PID={process.pid}')

            SystemLog.log_proxy(
                f'代理启动成功: 端口 {port}',
                details={'port': port, 'interface': interface, 'bind_ip': bind_ip, 'pid': process.pid}
            )

            return process.pid

        except Exception as e:
            logger.error(f'启动 Gost 失败: {e}')
            SystemLog.log_error('proxy', f'代理启动失败: {e}', details={'port': port})
            raise GostError(f'启动失败: {e}')

    def stop(self, port: int) -> bool:
        """停止 Socks5 代理

        Args:
            port: 监听端口

        Returns:
            是否成功停止
        """
        pid = self._read_pid(port)

        if not pid:
            logger.warning(f'端口 {port} 的代理 PID 文件不存在')
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f'Gost 代理已停止: 端口={port}, PID={pid}')

            SystemLog.log_proxy(
                f'代理停止成功: 端口 {port}',
                details={'port': port, 'pid': pid}
            )

        except ProcessLookupError:
            logger.warning(f'进程 {pid} 不存在')
        except Exception as e:
            logger.error(f'停止 Gost 失败: {e}')
            SystemLog.log_error('proxy', f'代理停止失败: {e}', details={'port': port})
            return False
        finally:
            self._remove_pid(port)
            # 关闭防火墙端口
            self._close_firewall_port(port)

        return True

    def restart(self, port: int, bind_ip: str, interface: str = '') -> int:
        """重启代理"""
        self.stop(port)
        return self.start(port, bind_ip, interface)

    def get_status(self, port: int) -> dict:
        """获取代理状态"""
        pid = self._read_pid(port)
        running = pid and self._is_process_running(pid)

        return {
            'port': port,
            'running': running,
            'pid': pid if running else None,
            'log_file': str(self._get_log_file(port))
        }

    def cleanup_stale(self):
        """清理僵死的进程记录"""
        cleaned = 0
        for pid_file in self.pid_dir.glob('*.pid'):
            try:
                port = int(pid_file.stem)
                pid = int(pid_file.read_text().strip())
                if not self._is_process_running(pid):
                    pid_file.unlink()
                    cleaned += 1
                    logger.info(f'清理僵死 PID 文件: 端口={port}')
            except (ValueError, IOError):
                pid_file.unlink()
                cleaned += 1

        return cleaned
