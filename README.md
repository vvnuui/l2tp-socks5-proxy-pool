# L2TP Socks5 代理池管理系统

基于 Ubuntu 的 L2TP 多出口 Socks5 代理池管理系统，通过 Web UI 管理 L2TP 服务端，实现多个 L2TP Client 拨入后的策略路由隔离和 Socks5 代理映射。

## 功能特性

- **L2TP 服务端管理**: 自动配置 xl2tpd 和 StrongSwan
- **账号管理**: Web 界面管理 L2TP 用户，支持批量创建
- **策略路由**: 自动为每个 Client 创建独立路由表
- **Socks5 代理**: 集成 Gost 引擎，支持端口到出口 IP 的映射
- **实时监控**: 看板显示连接状态、代理运行情况
- **日志系统**: 记录上线/下线、路由变更等事件

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
- Gost (Socks5 代理引擎)

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

### 3. 使用 Docker 部署

```bash
# 一键初始化
make setup

# 或手动执行
docker-compose build
docker-compose up -d
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### 4. 安装系统组件

网络组件需要在主机上运行：

```bash
sudo bash backend/scripts/setup.sh
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
│   │   ├── network/         # 网络配置
│   │   └── logs/            # 日志系统
│   └── scripts/             # 系统脚本
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── api/             # API 封装
│       ├── views/           # 页面视图
│       ├── stores/          # Pinia 状态
│       └── router/          # 路由配置
├── docker/                  # Docker 配置
├── docker-compose.yml
└── Makefile
```

## API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| /api/accounts/ | GET/POST | 账号列表/创建 |
| /api/accounts/{id}/ | GET/PATCH/DELETE | 账号详情/修改/删除 |
| /api/connections/ | GET | 连接列表 |
| /api/connections/online/ | POST | Client 上线回调 |
| /api/connections/offline/ | POST | Client 下线回调 |
| /api/proxies/ | GET/POST | 代理配置列表/创建 |
| /api/proxies/{id}/start/ | POST | 启动代理 |
| /api/proxies/{id}/stop/ | POST | 停止代理 |
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
- `/etc/ppp/ip-up.d/99-socks-proxy`
- `/etc/ppp/ip-down.d/99-socks-proxy`

环境变量：
- `SOCKS_API_URL`: API 回调地址
- `SOCKS_API_TOKEN`: API Token

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
make logs

# 进入后端容器
make shell

# 运行数据库迁移
make migrate

# 创建管理员
make createsuperuser
```

## 许可证

MIT License
