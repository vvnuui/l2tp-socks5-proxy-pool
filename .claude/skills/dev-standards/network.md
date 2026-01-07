# 网络脚本开发规范

## 1. Shell 脚本规范
- 首行声明: `#!/bin/bash`
- 启用严格模式: `set -euo pipefail`
- 脚本需要可执行权限: `chmod +x script.sh`

## 2. 脚本模板
```bash
#!/bin/bash
set -euo pipefail

# ============================================
# 脚本名称: setup_routing.sh
# 描述: 配置策略路由
# 作者: System
# 日期: 2024-01-01
# ============================================

# 常量定义
readonly LOG_FILE="/var/log/socks-proxy/routing.log"
readonly RT_TABLES="/etc/iproute2/rt_tables"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# 参数校验
if [[ $# -lt 2 ]]; then
    log_error "用法: $0 <interface> <table_id>"
    exit 1
fi

INTERFACE=$1
TABLE_ID=$2

# 主逻辑
main() {
    log "开始配置路由表 rt_${INTERFACE}"

    # 添加路由表
    if ! grep -q "^${TABLE_ID}" "$RT_TABLES"; then
        echo "${TABLE_ID} rt_${INTERFACE}" >> "$RT_TABLES"
    fi

    # 配置路由
    ip route add default dev "$INTERFACE" table "rt_${INTERFACE}"
    ip rule add fwmark "$TABLE_ID" table "rt_${INTERFACE}"

    log "路由配置完成"
}

main
```

## 3. PPP 钩子脚本规范

### ip-up.sh (Client 上线)
```bash
#!/bin/bash
# PPP 参数说明
INTERFACE=$1      # ppp0, ppp1, ...
TTY=$2            # 终端设备
SPEED=$3          # 连接速度
LOCAL_IP=$4       # 服务器 PPP IP (如 10.0.0.1)
PEER_IP=$5        # 客户端分配的 IP (如 10.0.0.2)
IPPARAM=${6:-}    # 额外参数

# 注意: PPP 参数中 LOCAL_IP 是服务器端 IP，PEER_IP 是客户端 IP
# Gost 绑定到 PPP 接口，流量通过隧道到达客户端

# API 配置
API_URL="http://127.0.0.1:8000/api/ppp/callback/"
PPP_HOOK_TOKEN="your-secret-token"

# 回调 API
curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -H "X-PPP-Token: $PPP_HOOK_TOKEN" \
    -d "{
        \"action\": \"up\",
        \"interface\": \"$INTERFACE\",
        \"local_ip\": \"$PEER_IP\",
        \"peer_ip\": \"$LOCAL_IP\",
        \"username\": \"$PEERNAME\"
    }"

logger -t ppp-hook "ip-up: interface=$INTERFACE server=$LOCAL_IP client=$PEER_IP"
```

### ip-down.sh (Client 下线)
```bash
#!/bin/bash
INTERFACE=$1
LOCAL_IP=$4
PEER_IP=$5

API_URL="http://127.0.0.1:8000/api/ppp/callback/"
PPP_HOOK_TOKEN="your-secret-token"

curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -H "X-PPP-Token: $PPP_HOOK_TOKEN" \
    -d "{
        \"action\": \"down\",
        \"interface\": \"$INTERFACE\",
        \"local_ip\": \"$PEER_IP\",
        \"peer_ip\": \"$LOCAL_IP\"
    }" || true

logger -t ppp-hook "ip-down: interface=$INTERFACE"
```

## 4. 策略路由配置规范 (基于源 IP)

### 配置源路由
```bash
# 变量
INTERFACE="ppp0"
TABLE_ID="100"
TABLE_NAME="rt_user_1"
SERVER_PPP_IP="10.0.0.1"   # 服务器 PPP IP，Gost 绑定此接口
CLIENT_IP="10.0.0.2"        # 客户端 IP，流量通过此 IP 出去

# 1. 创建路由表 (如果不存在)
grep -q "^${TABLE_ID}" /etc/iproute2/rt_tables || \
    echo "${TABLE_ID} ${TABLE_NAME}" >> /etc/iproute2/rt_tables

# 2. 添加默认路由：通过客户端 IP 出去
ip route replace default via "$CLIENT_IP" dev "$INTERFACE" table "$TABLE_NAME"

# 3. 添加路由策略：来自服务器 PPP IP 的流量使用此路由表
ip rule del from "$SERVER_PPP_IP" table "$TABLE_NAME" 2>/dev/null || true
ip rule add from "$SERVER_PPP_IP" table "$TABLE_NAME" priority 100
```

### 清理路由表
```bash
cleanup_source_routing() {
    local table_name=$1
    local local_ip=$2

    # 删除路由策略
    ip rule del from "$local_ip" table "$table_name" 2>/dev/null || true

    # 删除路由
    ip route del default table "$table_name" 2>/dev/null || true
}
```

## 5. Gost v3 代理命令规范

### 启动代理 (Gost v3)
```bash
# Gost v3 使用 interface 参数绑定出站接口
# 格式: gost -L socks5://:port?interface=ppp0

# 无认证模式
gost -L "socks5://:10800?interface=ppp0"

# 带认证模式
gost -L "socks5://user:pass@:10800?interface=ppp0"

# 后台运行并记录 PID
start_gost() {
    local port=$1
    local interface=$2
    local log_dir="/var/log/gost"
    local pid_dir="/var/run/gost"

    mkdir -p "$log_dir" "$pid_dir"

    nohup gost -L "socks5://:${port}?interface=${interface}" \
        > "${log_dir}/${port}.log" 2>&1 &

    echo $! > "${pid_dir}/${port}.pid"
    logger -t gost "Started Gost v3 on port $port, interface=$interface"
}
```

### 停止代理
```bash
stop_gost() {
    local port=$1
    local pid_file="/var/run/gost/${port}.pid"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        kill "$pid" 2>/dev/null || true
        rm -f "$pid_file"
        logger -t gost "Stopped Gost on port $port"
    fi
}
```

## 6. L2TP/IPSec 配置规范

### xl2tpd.conf 模板
```ini
[global]
listen-addr = 0.0.0.0
port = 1701
ipsec saref = no

[lns default]
ip range = 10.0.0.2-10.0.3.254
local ip = 10.0.0.1
require chap = yes
refuse pap = yes
require authentication = yes
name = l2tp-server
pppoptfile = /etc/ppp/options.xl2tpd
length bit = yes
```

### chap-secrets 格式
```
# client    server    secret    IP addresses
user1       *         password1  10.0.0.2
user2       *         password2  10.0.0.3
```

## 7. 流量路径说明

```
用户请求
    ↓
Socks5 代理 (Gost v3, interface=ppp0)
    ↓
PPP 接口 (ppp0, IP=10.0.0.1)
    ↓
L2TP 隧道
    ↓
客户端 (10.0.0.2)
    ↓
客户端 NAT (MASQUERADE)
    ↓
客户端公网 IP 出口
```

## 8. 错误处理规范
```bash
# 安全执行命令
safe_exec() {
    local cmd=$1
    local msg=$2

    if ! eval "$cmd"; then
        log_error "$msg: $cmd"
        return 1
    fi
}

# 示例
safe_exec "ip route replace default via 10.0.0.2 dev ppp0 table rt_user_1" "添加路由失败"
```

## 9. 权限要求

### 宿主机
- PPP 钩子脚本需要 root 权限
- 脚本位置: `/etc/ppp/ip-up.d/` 和 `/etc/ppp/ip-down.d/`
- 需要安装: `curl`, `iproute2`, `iptables`, `gost` (v3)

### Docker 容器
- `NET_ADMIN`: 管理网络接口和路由
- `NET_RAW`: 支持 SO_BINDTODEVICE (Gost 接口绑定)

```yaml
# docker-compose.yml
services:
  backend:
    cap_add:
      - NET_ADMIN
      - NET_RAW
```

## 10. 故障排查

### 检查路由配置
```bash
# 查看路由规则
ip rule list

# 查看特定路由表
ip route show table rt_user_1

# 验证路由
ip route get 8.8.8.8 from 10.0.0.1
```

### 检查 Gost 进程
```bash
# 查看进程
ps aux | grep gost

# 检查端口监听
ss -tlnp | grep gost

# 查看日志
cat /var/log/gost/10800.log
```

### 检查 PPP 接口
```bash
# 查看 PPP 接口
ip addr show | grep ppp

# 查看连接状态
cat /var/run/ppp*.pid
```
