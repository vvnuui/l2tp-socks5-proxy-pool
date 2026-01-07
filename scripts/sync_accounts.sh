#!/bin/bash
#
# 同步数据库账号到 chap-secrets
# 在宿主机运行此脚本
#

set -e

CHAP_SECRETS="/etc/ppp/chap-secrets"
PROJECT_DIR="${PROJECT_DIR:-/www/socks}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# 检查 root 权限
if [[ $EUID -ne 0 ]]; then
    echo "请使用 root 权限运行此脚本"
    exit 1
fi

# 备份原文件
if [[ -f "$CHAP_SECRETS" ]]; then
    cp "$CHAP_SECRETS" "${CHAP_SECRETS}.bak.$(date +%Y%m%d%H%M%S)"
    log_info "已备份 $CHAP_SECRETS"
fi

# 写入头部
cat > "$CHAP_SECRETS" << 'EOF'
# L2TP Socks5 Proxy Pool - chap-secrets
# 由 sync_accounts.sh 自动生成
# 格式: username server password ip
#
EOF

# 从数据库获取账号并写入
log_info "从数据库同步账号..."

cd "$PROJECT_DIR"
docker compose exec -T backend python manage.py shell -c "
from apps.accounts.models import L2TPAccount
for a in L2TPAccount.objects.filter(is_active=True):
    print(f'{a.username}\t*\t{a.password}\t{a.assigned_ip}')
" >> "$CHAP_SECRETS"

# 设置权限
chmod 600 "$CHAP_SECRETS"

# 统计
COUNT=$(grep -v "^#" "$CHAP_SECRETS" | grep -v "^$" | wc -l)
log_info "同步完成，共 $COUNT 个账号"

# 显示内容
echo ""
echo "=== $CHAP_SECRETS ==="
cat "$CHAP_SECRETS"
echo "===================="
