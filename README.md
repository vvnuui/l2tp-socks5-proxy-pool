# L2TP Socks5 代理池管理系统

> 版本: 1.1.0

基于 Ubuntu 的 L2TP 多出口 Socks5 代理池管理系统，通过 Web UI 管理 L2TP 服务端，实现多个 L2TP Client 拨入后的策略路由隔离和 Socks5 代理映射。

## 功能特性

- **L2TP 服务端管理**: 自动配置 xl2tpd 和 StrongSwan
- **账号管理**: Web 界面管理 L2TP 用户，支持批量创建
- **策略路由**: 自动为每个 Client 创建独立路由表，基于源 IP 的策略路由
- **多出口代理**: 集成 Gost v3 引擎，支持接口绑定，流量从客户端公网 IP 出口
- **实时监控**: 看板显示连接状态、代理运行情况
- **日志系统**: 记录上线/下线、路由变更等事件

## 工作原理

```
用户请求 → Socks5 代理 (Gost v3) → PPP 接口绑定 → L2TP 隧道 → 客户端 NAT → 客户端公网 IP 出口
```

每个 L2TP 客户端拨入后：
1. 服务端分配 PPP 接口 (ppp0, ppp1, ...)
2. 自动配置策略路由，将特定源 IP 的流量路由到客户端
3. Gost v3 使用 `interface` 参数绑定出站流量到对应 PPP 接口
4. 流量经过 L2TP 隧道到达客户端，由客户端 NAT 后从其公网 IP 出口

## 技术栈

**后端**
- Django 5.2 + Django REST Framework
- Celery (异步任务)
- PostgreSQL + Redis

**前端**
- Vue 3 + Vite
- Element Plus
- Pinia + TypeScript

**网络组件**
- xl2tpd + StrongSwan (L2TP/IPSec)
- iproute2 + iptables (策略路由)
- Gost v3 (Socks5 代理引擎，支持接口绑定)

## 系统要求

- Ubuntu 22.04+
- Docker + Docker Compose
- Python 3.12+ (开发环境)
- Node.js 20+ (开发环境)

## 快速开始

### 1. 克隆项目

```bash
cd /www/socks
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改必要的配置
```

### 3. 安装宿主机组件

网络组件需要在宿主机上运行：

```bash
# 安装 L2TP 服务端、Gost v3 等组件
sudo bash scripts/install.sh
```

### 4. 使用 Docker 部署

```bash
# 构建并启动
docker compose build
docker compose up -d

# 数据库迁移
docker compose exec backend python manage.py migrate

# 创建管理员
docker compose exec backend python manage.py createsuperuser
```

### 5. 访问系统

- 前端: http://localhost
- 后端 API: http://localhost:8000/api/

## 目录结构

```
/www/socks/
├── backend/                 # Django 后端
│   ├── config/              # Django 配置
│   ├── apps/                # 应用模块
│   │   ├── accounts/        # L2TP 账号管理
│   │   ├── connections/     # 连接状态
│   │   ├── network/         # 网络配置 (Gost, 路由)
│   │   └── logs/            # 日志系统
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── api/             # API 封装
│       ├── views/           # 页面视图
│       ├── stores/          # Pinia 状态
│       └── router/          # 路由配置
├── scripts/                 # 安装脚本
│   └── install.sh           # 宿主机安装脚本
├── docker/                  # Docker 配置
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
└── Makefile
```

## API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| /api/accounts/ | GET/POST | 账号列表/创建 |
| /api/accounts/{id}/ | GET/PATCH/DELETE | 账号详情/修改/删除 |
| /api/connections/ | GET | 连接列表 |
| /api/ppp/callback/ | POST | PPP 上线/下线回调 |
| /api/proxies/ | GET/POST | 代理配置列表/创建 |
| /api/proxies/{id}/start/ | POST | 启动代理 |
| /api/proxies/{id}/stop/ | POST | 停止代理 |
| /api/proxies/{id}/restart/ | POST | 重启代理 |
| /api/proxies/{id}/status/ | GET | 获取代理状态 |
| /api/dashboard/ | GET | 看板数据 |
| /api/logs/ | GET | 系统日志 |

## 配置说明

### IP 地址池

默认配置：
- 范围: 10.0.0.2 - 10.0.3.254 (1022 个地址)
- 服务端 IP: 10.0.0.1

### 代理端口

默认配置：
- 范围: 10800 - 11900 (1100 个端口)

### PPP 钩子

钩子脚本位置：
- `/etc/ppp/ip-up.d/99-socks-proxy` - 连接建立时回调
- `/etc/ppp/ip-down.d/99-socks-proxy` - 连接断开时回调

环境变量 (在 install.sh 中配置)：
- `API_URL`: API 回调地址 (默认 http://127.0.0.1:8000)
- `PPP_HOOK_TOKEN`: API Token

### Docker 容器权限

后端容器需要以下权限才能管理网络：
- `NET_ADMIN`: 管理网络接口和路由
- `NET_RAW`: 支持 SO_BINDTODEVICE (Gost 接口绑定)

## L2TP 客户端配置

客户端 (如爱快、RouterOS 等) 需要配置：

1. **L2TP 连接**: 连接到服务器的 L2TP 服务
2. **NAT/MASQUERADE**: 对来自 L2TP 隧道的流量进行 NAT
   ```
   # 示例 iptables 规则
   iptables -t nat -A POSTROUTING -s 10.0.0.0/22 -o wan -j MASQUERADE
   ```

## 开发指南

### 后端开发

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 进入后端容器
docker compose exec backend bash

# 运行数据库迁移
docker compose exec backend python manage.py migrate

# 创建管理员
docker compose exec backend python manage.py createsuperuser

# 重建容器
docker compose up -d --build
```

## 故障排查

### 代理流量未从客户端出口

1. 检查 Gost 版本是否为 v3：`gost -V`
2. 检查容器是否有 NET_RAW 权限
3. 检查客户端是否配置了 NAT
4. 检查策略路由：`ip rule list` 和 `ip route show table <table_name>`

### PPP 连接正常但代理不工作

1. 检查 PPP 钩子脚本：`cat /etc/ppp/ip-up.d/99-socks-proxy`
2. 查看系统日志：`journalctl -t ppp-hook`
3. 检查 Gost 进程：`ps aux | grep gost`

## 更新日志

### v1.1.0
- 升级 Gost v2 到 v3，支持出站接口绑定
- 实现基于源 IP 的策略路由
- 添加 CAP_NET_RAW 权限支持
- 优化 PPP 钩子脚本

### v1.0.0
- 初始版本
- L2TP 服务端管理
- Web UI 账号管理
- Socks5 代理基础功能

## 许可证

MIT License
