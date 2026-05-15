# Enterprise Knowledge Agent

企业知识代理项目，用于后续构建企业知识库、文档解析、RAG 问答和权限控制能力。

当前仓库只完成 Day 1：工程初始化和 Docker Compose 可运行底座。

## 技术栈

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Database: MySQL 8
- Vector Database: Qdrant
- Deployment: Docker Compose

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.css
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── uploads/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 启动方式

MacBook 只负责写代码和 Git 推送，不需要安装 Docker、MySQL、Python、Node.js 或 Qdrant。

i5 Ubuntu 服务器负责运行全部服务。服务器需要安装 Docker 和 Docker Compose，然后在项目根目录执行：

```bash
cp .env.example .env
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

停止服务：

```bash
docker compose down
```

## 常用访问地址

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- Backend API health: http://localhost:8000/api/health
- Backend version: http://localhost:8000/api/version
- Qdrant API: http://localhost:6333

如果在局域网访问 i5 Ubuntu 服务器，请把 `localhost` 替换为服务器 IP。

## Docker Compose 服务

- `mysql`: MySQL 8，数据持久化到 `mysql_data` volume
- `qdrant`: Qdrant，数据持久化到 `qdrant_data` volume
- `backend`: FastAPI，使用服务名 `mysql`、`qdrant` 连接依赖服务
- `frontend`: React + Vite + TypeScript，提供首页和后端连接检查按钮

`uploads/` 会挂载到后端容器的 `/app/uploads`。

## 当前进度

已完成：

- 项目根目录初始化
- Docker Compose 四服务编排
- MySQL 和 Qdrant volume 持久化
- FastAPI 健康检查接口
- React 首页与后端连接检查按钮

暂未实现：

- 登录
- 上传
- RAG
- RBAC
- MinIO
- Redis
- Celery
- Nginx

## 验证命令

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/health
curl http://localhost:8000/api/version
```
