---
name: dev-standards
description: L2TP Socks5 代理池项目开发规范。用于代码审查、编写代码、提交 PR 时检查命名约定、代码结构和最佳实践。
allowed-tools: Read, Grep, Glob
---

# L2TP Socks5 代理池 - 开发规范

## 技术栈
- **后端**: Django 5.2 + DRF + Celery + PostgreSQL + Redis
- **前端**: Vue 3 + Vite + Element Plus + Pinia + TypeScript
- **网络**: xl2tpd + StrongSwan + iproute2 + iptables + Gost

## 规范导航
- [后端规范](backend.md) - Django/Python 代码规范
- [前端规范](frontend.md) - Vue 3/TypeScript 规范
- [网络脚本规范](network.md) - Shell/网络配置规范
- [Git 规范](git.md) - 提交和分支规范

## 目录结构约定
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
│       ├── components/      # 公共组件
│       ├── views/           # 页面视图
│       ├── stores/          # Pinia 状态
│       └── router/          # 路由配置
└── docker/                  # Docker 配置
```

## 配置参数
| 配置项 | 值 |
|--------|-----|
| IP 地址池 | 10.0.0.0/22 (支持 1022 个 Client) |
| 代理认证 | 无需认证 |
| 端口范围 | 10800-11900 (支持 1100 个端口) |
| 部署方式 | Docker (Django/Redis/PostgreSQL) + 主机 (网络组件) |
