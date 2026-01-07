#!/bin/bash
#
# PPP 连接建立时的回调脚本
# 部署到: /etc/ppp/ip-up.d/99-socks-proxy
#

INTERFACE=$1
TTY=$2
SPEED=$3
LOCAL_IP=$4   # 服务器 IP (10.0.0.1)
PEER_IP=$5    # 客户端分配的 IP (10.0.0.2)
IPPARAM=$6

# 配置
API_URL="http://127.0.0.1:8000"
TOKEN="your-secret-token-change-me"
GOST_BIN="/usr/local/bin/gost"
GOST_LOG_DIR="/var/log/gost"
GOST_PID_DIR="/var/run/gost"

# 记录日志
logger -t ppp-hook "ip-up: interface=$INTERFACE server=$LOCAL_IP client=$PEER_IP"

# 创建目录
mkdir -p "$GOST_LOG_DIR" "$GOST_PID_DIR"

# 回调 API 通知上线
RESPONSE=$(curl -s -X POST "${API_URL}/api/ppp/callback/" \
    -H "Content-Type: application/json" \
    -H "X-PPP-Token: ${TOKEN}" \
    -d "{\"action\": \"up\", \"interface\": \"$INTERFACE\", \"local_ip\": \"$PEER_IP\", \"peer_ip\": \"$LOCAL_IP\", \"username\": \"$PEERNAME\"}")

logger -t ppp-hook "API response: $RESPONSE"

# 解析账号 ID
ACCOUNT_ID=$(echo "$RESPONSE" | sed -n 's/.*"account_id":\([0-9]*\).*/\1/p')

if [ -z "$ACCOUNT_ID" ]; then
    logger -t ppp-hook "Failed to get account_id from API"
    exit 0
fi

# 查询代理配置
PROXY_INFO=$(curl -s "${API_URL}/api/proxies/?account=${ACCOUNT_ID}" \
    -H "Authorization: Token ${TOKEN}" 2>/dev/null || \
    curl -s "${API_URL}/api/proxies/?account=${ACCOUNT_ID}")

# 解析代理端口
PORT=$(echo "$PROXY_INFO" | sed -n 's/.*"listen_port":\([0-9]*\).*/\1/p' | head -1)
AUTO_START=$(echo "$PROXY_INFO" | sed -n 's/.*"auto_start":\([a-z]*\).*/\1/p' | head -1)

logger -t ppp-hook "Account: $ACCOUNT_ID, Port: $PORT, AutoStart: $AUTO_START"

# 检查是否需要启动 Gost
if [ -z "$PORT" ]; then
    logger -t ppp-hook "No proxy port configured for account $ACCOUNT_ID"
    exit 0
fi

if [ "$AUTO_START" != "true" ]; then
    logger -t ppp-hook "Auto start disabled for port $PORT"
    exit 0
fi

# 检查 Gost 是否安装
if [ ! -x "$GOST_BIN" ]; then
    logger -t ppp-hook "Gost not found at $GOST_BIN"
    exit 0
fi

# 停止已存在的 Gost 进程
PID_FILE="$GOST_PID_DIR/gost_${PORT}.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# 启动 Gost 代理
LOG_FILE="$GOST_LOG_DIR/gost_${PORT}.log"
$GOST_BIN -L "socks5://:${PORT}?interface=${INTERFACE}" \
    >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

logger -t ppp-hook "Started Gost PID=$NEW_PID on port $PORT via $INTERFACE"

# 更新数据库中的状态
curl -s -X POST "${API_URL}/api/proxies/${ACCOUNT_ID}/update_status/" \
    -H "Content-Type: application/json" \
    -H "X-PPP-Token: ${TOKEN}" \
    -d "{\"is_running\": true, \"gost_pid\": $NEW_PID}" 2>/dev/null || true

exit 0
