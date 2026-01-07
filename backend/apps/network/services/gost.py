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
        """启动 Socks5 代理

        Args:
            port: 监听端口
            bind_ip: 绑定出口 IP
            interface: 绑定接口名 (可选)

        Returns:
            进程 PID

        Raises:
            GostError: 启动失败时
        """
        if self.is_running(port):
            raise GostError(f'端口 {port} 的代理已在运行')

        log_file = self._get_log_file(port)

        # 构建命令
        if interface:
            forward = f'forward://{bind_ip}:0?interface={interface}'
        else:
            forward = f'forward://{bind_ip}:0'

        cmd = [
            self.bin_path,
            '-L', f'socks5://0.0.0.0:{port}',
            '-F', forward
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
            logger.info(f'Gost 代理已启动: 端口={port}, PID={process.pid}')

            SystemLog.log_proxy(
                f'代理启动成功: 端口 {port}',
                details={'port': port, 'bind_ip': bind_ip, 'pid': process.pid}
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
