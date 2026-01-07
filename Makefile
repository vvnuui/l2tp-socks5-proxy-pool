.PHONY: help build up down logs shell migrate setup

help:
	@echo "L2TP Socks5 代理管理系统"
	@echo ""
	@echo "使用方法:"
	@echo "  make build      - 构建 Docker 镜像"
	@echo "  make up         - 启动所有服务"
	@echo "  make down       - 停止所有服务"
	@echo "  make logs       - 查看日志"
	@echo "  make shell      - 进入后端容器 shell"
	@echo "  make migrate    - 运行数据库迁移"
	@echo "  make setup      - 初始化系统环境"
	@echo "  make createsuperuser - 创建管理员账号"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend bash

migrate:
	docker-compose exec backend python manage.py migrate

makemigrations:
	docker-compose exec backend python manage.py makemigrations

createsuperuser:
	docker-compose exec backend python manage.py createsuperuser

setup:
	@echo "初始化系统环境..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "已创建 .env 文件，请修改配置"; \
	fi
	@echo "构建 Docker 镜像..."
	docker-compose build
	@echo "启动服务..."
	docker-compose up -d
	@echo "等待服务启动..."
	sleep 10
	@echo "运行数据库迁移..."
	docker-compose exec backend python manage.py migrate
	@echo ""
	@echo "初始化完成!"
	@echo "请运行以下命令创建管理员账号:"
	@echo "  make createsuperuser"
	@echo ""
	@echo "访问地址: http://localhost"

# 开发模式
dev-backend:
	cd backend && python manage.py runserver

dev-frontend:
	cd frontend && npm run dev

# 安装系统组件 (需要 root 权限)
install-system:
	sudo bash backend/scripts/setup.sh
