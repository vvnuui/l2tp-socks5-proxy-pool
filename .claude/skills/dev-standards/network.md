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
set -euo pipefail

# PPP 参数
INTERFACE=$1      # ppp0, ppp1, ...
TTY=$2            # 终端设备
SPEED=$3          # 连接速度
LOCAL_IP=$4       # 本地 IP
REMOTE_IP=$5      # 远端 IP
IPPARAM=${6:-}    # 额外参数

# API 配置
API_URL="http://127.0.0.1:8000/api/connections/online/"
API_TOKEN="your-secret-token"

# 日志
LOG_FILE="/var/log/ppp-hooks.log"
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UP] $1" >> "$LOG_FILE"
}

# 回调 API
callback_api() {
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Token $API_TOKEN" \
        -d "{
            \"interface\": \"$INTERFACE\",
            \"local_ip\": \"$LOCAL_IP\",
            \"remote_ip\": \"$REMOTE_IP\"
        }")

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
        log "API 回调失败: HTTP $http_code"
        return 1
    fi

    log "API 回调成功: $INTERFACE ($LOCAL_IP -> $REMOTE_IP)"
}

callback_api
```

### ip-down.sh (Client 下线)
```bash
#!/bin/bash
set -euo pipefail

INTERFACE=$1
API_URL="http://127.0.0.1:8000/api/connections/offline/"
API_TOKEN="your-secret-token"
LOG_FILE="/var/log/ppp-hooks.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DOWN] $1" >> "$LOG_FILE"
}

curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Token $API_TOKEN" \
    -d "{\"interface\": \"$INTERFACE\"}"

log "接口下线: $INTERFACE"
```

## 4. 策略路由配置规范

### 创建路由表
```bash
# 变量
INTERFACE="ppp1"
TABLE_ID="101"
TABLE_NAME="rt_ppp1"
PROXY_PORT="10801"

# 1. 创建路由表 (如果不存在)
grep -q "^${TABLE_ID}" /etc/iproute2/rt_tables || \
    echo "${TABLE_ID} ${TABLE_NAME}" >> /etc/iproute2/rt_tables

# 2. 添加默认路由到路由表
ip route add default dev "$INTERFACE" table "$TABLE_NAME"

# 3. 添加路由策略
ip rule add fwmark "$TABLE_ID" table "$TABLE_NAME" priority 100

# 4. 配置 iptables 打标签
iptables -t mangle -A OUTPUT -p tcp --dport "$PROXY_PORT" -j MARK --set-mark "$TABLE_ID"
```

### 清理路由表
```bash
cleanup_routing() {
    local interface=$1
    local table_id=$2
    local table_name="rt_${interface}"
    local proxy_port=$((10800 + table_id - 100))

    # 删除 iptables 规则
    iptables -t mangle -D OUTPUT -p tcp --dport "$proxy_port" \
        -j MARK --set-mark "$table_id" 2>/dev/null || true

    # 删除路由策略
    ip rule del fwmark "$table_id" table "$table_name" 2>/dev/null || true

    # 删除路由
    ip route del default table "$table_name" 2>/dev/null || true
}
```

## 5. Gost 代理命令规范

### 启动代理
```bash
# 无认证模式
gost -L "socks5://0.0.0.0:10801" -F "forward://10.0.0.2:0?interface=ppp1"

# 带认证模式
gost -L "socks5://user:pass@0.0.0.0:10801" -F "forward://10.0.0.2:0?interface=ppp1"

# 后台运行并记录 PID
start_gost() {
    local port=$1
    local bind_ip=$2
    local interface=$3
    local log_dir="/var/log/gost"
    local pid_dir="/var/run/gost"

    mkdir -p "$log_dir" "$pid_dir"

    nohup gost -L "socks5://0.0.0.0:${port}" \
        -F "forward://${bind_ip}:0?interface=${interface}" \
        > "${log_dir}/${port}.log" 2>&1 &

    echo $! > "${pid_dir}/${port}.pid"
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

## 7. 错误处理规范
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
safe_exec "ip route add default dev ppp1 table rt_ppp1" "添加路由失败"
```

## 8. 权限要求
- PPP 钩子脚本需要 root 权限
- 脚本位置: `/etc/ppp/ip-up.d/` 和 `/etc/ppp/ip-down.d/`
- 需要安装: `curl`, `iproute2`, `iptables`
