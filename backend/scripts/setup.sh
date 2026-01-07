#!/bin/bash
set -euo pipefail

# ============================================
# 脚本名称: setup.sh
# 描述: L2TP Socks5 代理系统环境初始化脚本
# ============================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."

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

    log_info "系统依赖安装完成"
}

# 安装 Gost
install_gost() {
    log_info "安装 Gost..."

    local GOST_VERSION="3.0.0"
    local GOST_URL="https://github.com/go-gost/gost/releases/download/v${GOST_VERSION}/gost_${GOST_VERSION}_linux_amd64.tar.gz"
    local INSTALL_PATH="/usr/local/bin/gost"

    if [[ -f "$INSTALL_PATH" ]]; then
        log_warn "Gost 已安装，跳过"
        return 0
    fi

    cd /tmp
    wget -q "$GOST_URL" -O gost.tar.gz
    tar -xzf gost.tar.gz
    mv gost "$INSTALL_PATH"
    chmod +x "$INSTALL_PATH"
    rm -f gost.tar.gz

    log_info "Gost 安装完成: $("$INSTALL_PATH" -V)"
}

# 配置 xl2tpd
configure_xl2tpd() {
    log_info "配置 xl2tpd..."

    local LOCAL_IP="${PROXY_LOCAL_IP:-10.0.0.1}"
    local IP_RANGE_START="${PROXY_IP_POOL_START:-10.0.0.2}"
    local IP_RANGE_END="${PROXY_IP_POOL_END:-10.0.3.254}"

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

    cat > /etc/ppp/options.xl2tpd << EOF
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
        cat > /etc/ppp/chap-secrets << EOF
# Secrets for authentication using CHAP
# client    server    secret    IP addresses
EOF
    fi

    log_info "xl2tpd 配置完成"
}

# 配置 StrongSwan
configure_strongswan() {
    log_info "配置 StrongSwan..."

    local SERVER_IP="${SERVER_IP:-$(curl -s ifconfig.me)}"

    cat > /etc/ipsec.conf << EOF
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

conn l2tp-psk
    type=transport
    left=%defaultroute
    leftprotoport=17/1701
    right=%any
    rightprotoport=17/%any
    auto=add
EOF

    # 设置 PSK (请在生产环境中修改)
    local PSK="${IPSEC_PSK:-YourSharedSecretHere}"
    cat > /etc/ipsec.secrets << EOF
: PSK "${PSK}"
EOF

    chmod 600 /etc/ipsec.secrets

    log_info "StrongSwan 配置完成"
}

# 配置内核参数
configure_kernel() {
    log_info "配置内核参数..."

    cat > /etc/sysctl.d/99-l2tp-proxy.conf << EOF
# IP 转发
net.ipv4.ip_forward = 1

# 禁用 ICMP 重定向
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# 策略路由支持
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
EOF

    sysctl -p /etc/sysctl.d/99-l2tp-proxy.conf

    log_info "内核参数配置完成"
}

# 安装 PPP 钩子脚本
install_ppp_hooks() {
    log_info "安装 PPP 钩子脚本..."

    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # 创建目录
    mkdir -p /etc/ppp/ip-up.d /etc/ppp/ip-down.d

    # 复制脚本
    cp "$SCRIPT_DIR/ip-up.sh" /etc/ppp/ip-up.d/99-socks-proxy
    cp "$SCRIPT_DIR/ip-down.sh" /etc/ppp/ip-down.d/99-socks-proxy

    # 设置权限
    chmod +x /etc/ppp/ip-up.d/99-socks-proxy
    chmod +x /etc/ppp/ip-down.d/99-socks-proxy

    log_info "PPP 钩子脚本安装完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."

    mkdir -p /var/log/gost
    mkdir -p /var/run/gost
    mkdir -p /var/log/socks-proxy

    log_info "目录创建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    systemctl enable xl2tpd
    systemctl enable strongswan-starter

    systemctl restart strongswan-starter
    systemctl restart xl2tpd

    log_info "服务已启动"
}

# 主函数
main() {
    log_info "开始初始化 L2TP Socks5 代理系统..."

    check_root
    install_dependencies
    install_gost
    configure_xl2tpd
    configure_strongswan
    configure_kernel
    install_ppp_hooks
    create_directories
    start_services

    log_info "============================================"
    log_info "初始化完成!"
    log_info "请配置以下环境变量后重启 PPP 钩子:"
    log_info "  SOCKS_API_URL - API 回调地址"
    log_info "  SOCKS_API_TOKEN - API Token"
    log_info "============================================"
}

main "$@"
