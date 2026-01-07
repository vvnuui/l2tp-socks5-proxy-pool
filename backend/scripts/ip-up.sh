#!/bin/bash
set -euo pipefail

# ============================================
# 脚本名称: ip-up.sh
# 描述: PPP Client 上线钩子脚本
# 位置: /etc/ppp/ip-up.d/99-socks-proxy
# ============================================

# PPP 传入的参数
INTERFACE=$1      # ppp0, ppp1, ...
TTY=$2            # 终端设备
SPEED=$3          # 连接速度
LOCAL_IP=$4       # 本地分配的 IP (Client 端)
REMOTE_IP=$5      # 远端 IP (Server 端)
IPPARAM=${6:-}    # 额外参数

# 配置
API_URL="${SOCKS_API_URL:-http://127.0.0.1:8000/api/connections/online/}"
API_TOKEN="${SOCKS_API_TOKEN:-your-secret-token-change-me}"
LOG_FILE="/var/log/ppp-hooks.log"
MAX_RETRIES=3
RETRY_DELAY=2

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UP] $1" >> "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UP] ERROR: $1" >> "$LOG_FILE"
}

# 回调 API
callback_api() {
    local retry=0
    local response
    local http_code

    while [[ $retry -lt $MAX_RETRIES ]]; do
        response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
            -H "Content-Type: application/json" \
            -H "Authorization: Token $API_TOKEN" \
            --connect-timeout 5 \
            --max-time 10 \
            -d "{
                \"interface\": \"$INTERFACE\",
                \"local_ip\": \"$LOCAL_IP\",
                \"peer_ip\": \"$REMOTE_IP\"
            }" 2>/dev/null) || true

        http_code=$(echo "$response" | tail -n1)

        if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
            log "API 回调成功: $INTERFACE ($LOCAL_IP)"
            return 0
        fi

        retry=$((retry + 1))
        log_error "API 回调失败 (尝试 $retry/$MAX_RETRIES): HTTP $http_code"
        sleep $RETRY_DELAY
    done

    log_error "API 回调最终失败: $INTERFACE"
    return 1
}

# 主逻辑
main() {
    log "Client 上线: interface=$INTERFACE, local_ip=$LOCAL_IP, remote_ip=$REMOTE_IP"
    callback_api
}

main
