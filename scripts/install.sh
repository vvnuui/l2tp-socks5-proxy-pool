#!/bin/bash
#
# L2TP Socks5 代理池 - 宿主机安装脚本
# 在宿主机上运行此脚本安装和配置网络组件
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 权限运行此脚本"
        exit 1
    fi
}

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOCAL_IP="${LOCAL_IP:-10.0.0.1}"
IP_RANGE_START="${IP_RANGE_START:-10.0.0.2}"
IP_RANGE_END="${IP_RANGE_END:-10.0.3.254}"
IPSEC_PSK="${IPSEC_PSK:-your-preshared-key-change-me}"
API_URL="${API_URL:-http://127.0.0.1:8000}"
PPP_HOOK_TOKEN="${PPP_HOOK_TOKEN:-your-secret-token-change-me}"
GOST_VERSION="${GOST_VERSION:-2.11.5}"

# 安装依赖包
install_dependencies() {
    log_info "安装依赖包..."
    apt-get update
    apt-get install -y \
        xl2tpd \
        strongswan \
        strongswan-pki \
        libstrongswan-extra-plugins \
        ppp \
        iptables \
        iproute2 \
        curl \
        wget \
        jq
}

# 配置 StrongSwan (IPSec)
configure_strongswan() {
    log_info "配置 StrongSwan..."

    # ipsec.conf
    cat > /etc/ipsec.conf << 'EOF'
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    ikelifetime=60m
    keylife=20m
    rekeymargin=3m
    keyingtries=1
    keyexchange=ikev1
    authby=secret
    ike=aes128-sha1-modp2048!
    esp=aes128-sha1!

conn L2TP-PSK
    type=transport
    left=%defaultroute
    leftprotoport=17/1701
    right=%any
    rightprotoport=17/%any
    auto=add
EOF

    # ipsec.secrets
    cat > /etc/ipsec.secrets << EOF
: PSK "${IPSEC_PSK}"
EOF
    chmod 600 /etc/ipsec.secrets

    systemctl enable strongswan-starter
    systemctl restart strongswan-starter
    log_info "StrongSwan 配置完成"
}

# 配置 xl2tpd
configure_xl2tpd() {
    log_info "配置 xl2tpd..."

    # xl2tpd.conf
    cat > /etc/xl2tpd/xl2tpd.conf << EOF
[global]
listen-addr = 0.0.0.0
port = 1701
ipsec saref = no

[lns default]
ip range = ${IP_RANGE_START}-${IP_RANGE_END}
local ip = ${LOCAL_IP}
require chap = yes
refuse pap = yes
require authentication = yes
name = l2tp-server
pppoptfile = /etc/ppp/options.xl2tpd
length bit = yes
EOF

    # PPP 选项
    cat > /etc/ppp/options.xl2tpd << 'EOF'
ipcp-accept-local
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
EOF

    # 初始化 chap-secrets
    if [[ ! -f /etc/ppp/chap-secrets ]]; then
        cat > /etc/ppp/chap-secrets << 'EOF'
# L2TP Socks5 Proxy Pool - chap-secrets
# 格式: username server password ip
# 由系统自动管理，请勿手动编辑
EOF
    fi
    chmod 600 /etc/ppp/chap-secrets

    systemctl enable xl2tpd
    systemctl restart xl2tpd
    log_info "xl2tpd 配置完成"
}

# 配置 PPP 钩子脚本
configure_ppp_hooks() {
    log_info "配置 PPP 钩子脚本..."

    # ip-up 钩子（包含 Gost 自动启动）
    cat > /etc/ppp/ip-up.d/99-socks-proxy << EOF
#!/bin/bash
#
# PPP 连接建立时的回调脚本
# 1. 通知 API 客户端上线
# 2. 自动启动 Gost 代理
#

INTERFACE=\$1
TTY=\$2
SPEED=\$3
LOCAL_IP=\$4    # 服务器 IP (10.0.0.1)
PEER_IP=\$5     # 客户端分配的 IP (10.0.0.2)
IPPARAM=\$6

# 配置
API_URL="${API_URL}"
TOKEN="${PPP_HOOK_TOKEN}"
GOST_BIN="/usr/local/bin/gost"
GOST_LOG_DIR="/var/log/gost"
GOST_PID_DIR="/var/run/gost"

# 记录日志
logger -t ppp-hook "ip-up: interface=\$INTERFACE server=\$LOCAL_IP client=\$PEER_IP"

# 创建目录
mkdir -p "\$GOST_LOG_DIR" "\$GOST_PID_DIR"

# 回调 API 通知上线
RESPONSE=\$(curl -s -X POST "\${API_URL}/api/ppp/callback/" \\
    -H "Content-Type: application/json" \\
    -H "X-PPP-Token: \${TOKEN}" \\
    -d "{\"action\": \"up\", \"interface\": \"\$INTERFACE\", \"local_ip\": \"\$PEER_IP\", \"peer_ip\": \"\$LOCAL_IP\", \"username\": \"\$PEERNAME\"}")

logger -t ppp-hook "API response: \$RESPONSE"

# 解析账号 ID
ACCOUNT_ID=\$(echo "\$RESPONSE" | sed -n 's/.*"account_id":\([0-9]*\).*/\1/p')

if [ -z "\$ACCOUNT_ID" ]; then
    logger -t ppp-hook "Failed to get account_id from API"
    exit 0
fi

# 查询代理配置
PROXY_INFO=\$(curl -s "\${API_URL}/api/proxies/?account=\${ACCOUNT_ID}")

# 解析代理端口和自动启动设置
PORT=\$(echo "\$PROXY_INFO" | sed -n 's/.*"listen_port":\([0-9]*\).*/\1/p' | head -1)
AUTO_START=\$(echo "\$PROXY_INFO" | sed -n 's/.*"auto_start":\([a-z]*\).*/\1/p' | head -1)

logger -t ppp-hook "Account: \$ACCOUNT_ID, Port: \$PORT, AutoStart: \$AUTO_START"

# 检查是否需要启动 Gost
if [ -z "\$PORT" ]; then
    logger -t ppp-hook "No proxy port configured for account \$ACCOUNT_ID"
    exit 0
fi

if [ "\$AUTO_START" != "true" ]; then
    logger -t ppp-hook "Auto start disabled for port \$PORT"
    exit 0
fi

# 检查 Gost 是否安装
if [ ! -x "\$GOST_BIN" ]; then
    logger -t ppp-hook "Gost not found at \$GOST_BIN"
    exit 0
fi

# 停止已存在的 Gost 进程
PID_FILE="\$GOST_PID_DIR/gost_\${PORT}.pid"
if [ -f "\$PID_FILE" ]; then
    OLD_PID=\$(cat "\$PID_FILE")
    if kill -0 "\$OLD_PID" 2>/dev/null; then
        kill "\$OLD_PID" 2>/dev/null
        sleep 1
    fi
    rm -f "\$PID_FILE"
fi

# 启动 Gost 代理
LOG_FILE="\$GOST_LOG_DIR/gost_\${PORT}.log"
\$GOST_BIN -L "socks5://:\${PORT}?interface=\${INTERFACE}" \\
    >> "\$LOG_FILE" 2>&1 &

NEW_PID=\$!
echo "\$NEW_PID" > "\$PID_FILE"

logger -t ppp-hook "Started Gost PID=\$NEW_PID on port \$PORT via \$INTERFACE"

exit 0
EOF
    chmod +x /etc/ppp/ip-up.d/99-socks-proxy

    # ip-down 钩子（包含 Gost 自动停止）
    cat > /etc/ppp/ip-down.d/99-socks-proxy << EOF
#!/bin/bash
#
# PPP 连接断开时的回调脚本
# 1. 通知 API 客户端下线
# 2. 自动停止 Gost 代理
#

INTERFACE=\$1
TTY=\$2
SPEED=\$3
LOCAL_IP=\$4
PEER_IP=\$5
IPPARAM=\$6

# 配置
API_URL="${API_URL}"
TOKEN="${PPP_HOOK_TOKEN}"
GOST_PID_DIR="/var/run/gost"

# 记录日志
logger -t ppp-hook "ip-down: interface=\$INTERFACE server=\$LOCAL_IP client=\$PEER_IP"

# 回调 API 通知下线
curl -s -X POST "\${API_URL}/api/ppp/callback/" \\
    -H "Content-Type: application/json" \\
    -H "X-PPP-Token: \${TOKEN}" \\
    -d "{\"action\": \"down\", \"interface\": \"\$INTERFACE\", \"local_ip\": \"\$PEER_IP\", \"peer_ip\": \"\$LOCAL_IP\"}" || true

# 停止通过该接口的 Gost 进程
for PID_FILE in "\$GOST_PID_DIR"/gost_*.pid; do
    if [ -f "\$PID_FILE" ]; then
        PID=\$(cat "\$PID_FILE")
        PORT=\$(basename "\$PID_FILE" | sed 's/gost_\([0-9]*\)\.pid/\1/')

        if kill -0 "\$PID" 2>/dev/null; then
            # 检查进程命令行是否包含该接口
            if grep -q "\$INTERFACE" /proc/\$PID/cmdline 2>/dev/null; then
                kill "\$PID" 2>/dev/null
                rm -f "\$PID_FILE"
                logger -t ppp-hook "Stopped Gost PID=\$PID on port \$PORT"
            fi
        else
            rm -f "\$PID_FILE"
        fi
    fi
done

exit 0
EOF
    chmod +x /etc/ppp/ip-down.d/99-socks-proxy

    log_info "PPP 钩子脚本配置完成"
}

# 安装 Gost
install_gost() {
    log_info "安装 Gost v${GOST_VERSION}..."

    if command -v gost &> /dev/null; then
        log_warn "Gost 已安装"
        return
    fi

    ARCH=$(uname -m)
    case $ARCH in
        x86_64) GOST_ARCH="amd64" ;;
        aarch64) GOST_ARCH="arm64" ;;
        *) log_error "不支持的架构: $ARCH"; exit 1 ;;
    esac

    GOST_URL="https://github.com/ginuerzh/gost/releases/download/v${GOST_VERSION}/gost-linux-${GOST_ARCH}-${GOST_VERSION}.gz"

    log_info "下载 Gost: $GOST_URL"
    wget -q -O /tmp/gost.gz "$GOST_URL"
    gunzip -f /tmp/gost.gz
    mv /tmp/gost /usr/local/bin/gost
    chmod +x /usr/local/bin/gost

    # 创建目录
    mkdir -p /var/log/gost /var/run/gost

    log_info "Gost 安装完成: $(gost -V)"
}

# 配置内核参数和防火墙
configure_network() {
    log_info "配置网络参数..."

    # 内核参数
    cat > /etc/sysctl.d/99-l2tp-proxy.conf << 'EOF'
# L2TP Socks5 Proxy Pool
net.ipv4.ip_forward = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
EOF
    sysctl -p /etc/sysctl.d/99-l2tp-proxy.conf

    # 基础 iptables 规则
    iptables -A INPUT -p udp --dport 500 -j ACCEPT
    iptables -A INPUT -p udp --dport 4500 -j ACCEPT
    iptables -A INPUT -p udp --dport 1701 -j ACCEPT

    # NAT
    iptables -t nat -A POSTROUTING -s 10.0.0.0/22 -o eth0 -j MASQUERADE

    log_info "网络配置完成"
}

# 创建路由表配置
configure_routing_tables() {
    log_info "配置路由表..."

    # 备份原文件
    if [[ -f /etc/iproute2/rt_tables ]]; then
        cp /etc/iproute2/rt_tables /etc/iproute2/rt_tables.bak
    fi

    # 添加自定义路由表（预留 100-200）
    if ! grep -q "# L2TP Proxy Tables" /etc/iproute2/rt_tables 2>/dev/null; then
        echo "" >> /etc/iproute2/rt_tables
        echo "# L2TP Proxy Tables (100-200)" >> /etc/iproute2/rt_tables
    fi

    log_info "路由表配置完成"
}

# 显示安装信息
show_info() {
    PUBLIC_IP=$(curl -s ifconfig.me || echo "未知")

    echo ""
    echo "=============================================="
    echo "  L2TP Socks5 代理池安装完成"
    echo "=============================================="
    echo ""
    echo "服务状态:"
    echo "  StrongSwan: $(systemctl is-active strongswan-starter)"
    echo "  xl2tpd:     $(systemctl is-active xl2tpd)"
    echo ""
    echo "配置信息:"
    echo "  服务器公网 IP: $PUBLIC_IP"
    echo "  L2TP 本地 IP:  $LOCAL_IP"
    echo "  IP 地址池:     $IP_RANGE_START - $IP_RANGE_END"
    echo "  IPSec PSK:     $IPSEC_PSK"
    echo ""
    echo "重要文件:"
    echo "  /etc/ipsec.conf          - StrongSwan 配置"
    echo "  /etc/xl2tpd/xl2tpd.conf  - xl2tpd 配置"
    echo "  /etc/ppp/chap-secrets    - L2TP 用户认证"
    echo "  /etc/ppp/ip-up.d/        - PPP 连接钩子"
    echo ""
    echo "下一步:"
    echo "  1. 修改 /etc/ipsec.secrets 中的预共享密钥"
    echo "  2. 在 Web 界面创建 L2TP 账号"
    echo "  3. 客户端连接测试"
    echo ""
}

# 主函数
main() {
    check_root

    log_info "开始安装 L2TP Socks5 代理池..."

    install_dependencies
    configure_strongswan
    configure_xl2tpd
    configure_ppp_hooks
    install_gost
    configure_network
    configure_routing_tables

    show_info
}

# 运行
main "$@"
