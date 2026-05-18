# Enterprise Knowledge Agent

企业知识代理项目，用于后续构建企业知识库、文档解析、RAG 问答和权限控制能力。

当前仓库已完成 Day 2：简单登录与文档上传。

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

如果已经有 Day 1 的 `.env`，请确认其中 `APP_STAGE=Day 2`，然后重新构建后端和前端镜像。

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
- Login API: http://localhost:8000/api/auth/login
- Documents API: http://localhost:8000/api/documents
- Qdrant API: http://localhost:6333

如果在局域网访问 i5 Ubuntu 服务器，请把 `localhost` 替换为服务器 IP。

当前部署地址：

前端工作台：
http://192.168.3.93:5173

后端 API 文档：
http://192.168.3.93:8000/docs

Qdrant 控制台：
http://192.168.3.93:6333/dashboard

## Docker Compose 服务

- `mysql`: MySQL 8，数据持久化到 `mysql_data` volume
- `qdrant`: Qdrant，数据持久化到 `qdrant_data` volume
- `backend`: FastAPI，使用服务名 `mysql`、`qdrant` 连接依赖服务
- `frontend`: React + Vite + TypeScript，提供简单登录、文档上传和后端连接检查按钮

`uploads/` 会挂载到后端容器的 `/app/uploads`。

## 当前进度

已完成：

- Day 1 工程初始化和 Docker Compose 可运行底座
- FastAPI 健康检查接口
- React 首页与后端连接检查按钮
- Day 2 简单登录接口：`POST /api/auth/login`
- Day 2 文档上传接口：`POST /api/documents/upload`
- Day 2 文档列表接口：`GET /api/documents`
- 前端登录页、文档上传区域、已上传文档列表

暂未实现：

- PDF 解析
- 向量化
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
curl http://localhost:8000/api/documents
```

登录接口示例：

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

上传接口示例：

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@example.md"
```

# Day 1 已完成：

- 完成 FastAPI 后端工程初始化
- 完成 React + Vite 前端工程初始化
- 完成 MySQL 8 容器部署
- 完成 Qdrant 向量数据库容器部署
- 完成 Docker Compose 一键启动
- 完成前端调用后端健康检查

## Day 2 账号

- Username: `admin`
- Password: `admin123`
- Token: `day2-demo-token`
