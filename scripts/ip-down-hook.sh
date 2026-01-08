#!/bin/bash
#
# PPP 连接断开时的回调脚本
# 部署到: /etc/ppp/ip-down.d/99-socks-proxy
#

INTERFACE=$1
TTY=$2
SPEED=$3
LOCAL_IP=$4   # 服务器 IP
PEER_IP=$5    # 客户端 IP
IPPARAM=$6

# 配置
API_URL="http://127.0.0.1:8000"
TOKEN="your-secret-token-change-me"
GOST_PID_DIR="/var/run/gost"

# 采集接口流量统计（在接口关闭前获取）
BYTES_SENT=0
BYTES_RECEIVED=0
if [ -d "/sys/class/net/$INTERFACE/statistics" ]; then
    BYTES_SENT=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes 2>/dev/null || echo 0)
    BYTES_RECEIVED=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes 2>/dev/null || echo 0)
fi

# 记录日志
logger -t ppp-hook "ip-down: interface=$INTERFACE server=$LOCAL_IP client=$PEER_IP tx=$BYTES_SENT rx=$BYTES_RECEIVED"

# 回调 API 通知下线（包含流量数据）
curl -s -X POST "${API_URL}/api/ppp/callback/" \
    -H "Content-Type: application/json" \
    -H "X-PPP-Token: ${TOKEN}" \
    -d "{\"action\": \"down\", \"interface\": \"$INTERFACE\", \"local_ip\": \"$PEER_IP\", \"peer_ip\": \"$LOCAL_IP\", \"bytes_sent\": $BYTES_SENT, \"bytes_received\": $BYTES_RECEIVED}" || true

# 停止所有通过该接口的 Gost 进程
for PID_FILE in "$GOST_PID_DIR"/gost_*.pid; do
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        PORT=$(basename "$PID_FILE" | sed 's/gost_\([0-9]*\)\.pid/\1/')

        # 检查进程是否存在且绑定到该接口
        if kill -0 "$PID" 2>/dev/null; then
            # 检查进程命令行是否包含该接口
            if grep -q "$INTERFACE" /proc/$PID/cmdline 2>/dev/null; then
                kill "$PID" 2>/dev/null
                rm -f "$PID_FILE"
                logger -t ppp-hook "Stopped Gost PID=$PID on port $PORT"
            fi
        else
            rm -f "$PID_FILE"
        fi
    fi
done

exit 0
