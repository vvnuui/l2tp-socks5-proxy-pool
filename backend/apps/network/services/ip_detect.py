"""IP 地址检测服务"""

import socket
import subprocess
import urllib.request
import urllib.error


class IPDetectService:
    """自动检测公网和内网 IP"""

    # 用于检测公网 IP 的服务列表（按可靠性排序）
    PUBLIC_IP_SERVICES = [
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://ipecho.net/plain',
        'https://checkip.amazonaws.com',
        'https://api.ipify.org',
        'https://ip.3322.net',
    ]

    @classmethod
    def get_public_ip(cls, timeout: int = 5) -> str | None:
        """获取公网 IP 地址"""
        for service_url in cls.PUBLIC_IP_SERVICES:
            try:
                req = urllib.request.Request(
                    service_url,
                    headers={'User-Agent': 'curl/7.68.0'}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    ip = response.read().decode('utf-8').strip()
                    # 验证是否为有效 IP
                    socket.inet_aton(ip)
                    return ip
            except (urllib.error.URLError, socket.error, ValueError):
                continue
        return None

    @classmethod
    def get_private_ip(cls) -> str | None:
        """获取内网 IP 地址（非 127.0.0.1 的第一个 IP）"""
        try:
            # 方法1: 通过连接外部地址获取本机 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # 不需要真正连接，只是获取路由
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                return ip
            finally:
                s.close()
        except socket.error:
            pass

        try:
            # 方法2: 获取主机名对应的 IP
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip != '127.0.0.1':
                return ip
        except socket.error:
            pass

        return None

    @classmethod
    def detect_all(cls) -> dict:
        """检测所有 IP 地址"""
        return {
            'public_ip': cls.get_public_ip(),
            'private_ip': cls.get_private_ip()
        }

    @classmethod
    def get_exit_ip_via_proxy(cls, proxy_port: int, timeout: int = 10) -> str | None:
        """通过 socks5 代理检测出口 IP"""
        for service_url in cls.PUBLIC_IP_SERVICES:
            try:
                result = subprocess.run(
                    [
                        'curl', '-s', '--max-time', str(timeout),
                        '--socks5', f'127.0.0.1:{proxy_port}',
                        service_url
                    ],
                    capture_output=True,
                    text=True,
                    timeout=timeout + 2
                )
                if result.returncode == 0:
                    ip = result.stdout.strip()
                    # 验证是否为有效 IP
                    socket.inet_aton(ip)
                    return ip
            except (subprocess.TimeoutExpired, socket.error, ValueError):
                continue
        return None
