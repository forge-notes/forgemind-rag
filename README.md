# Enterprise Knowledge Agent

企业知识代理项目，用于后续构建企业知识库、文档解析、RAG 问答和权限控制能力。

当前仓库已完成 Day 3：文档解析与文本切分。

## 技术栈

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Database: MySQL 8
- Vector Database: Qdrant
- Deployment: Docker Compose
- PDF Parser: PyMuPDF

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

如果已经有 Day 1/Day 2 的 `.env`，请确认其中 `APP_STAGE=Day 3`，然后重新构建后端和前端镜像。

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
- `frontend`: React + Vite + TypeScript，提供登录、上传、解析和 chunk 预览

`uploads/` 会挂载到后端容器的 `/app/uploads`。

## 当前进度

已完成：

- Day 1 工程初始化和 Docker Compose 可运行底座
- Day 2 简单登录、PDF/Markdown 上传、uploads 文件列表展示
- Day 3 MySQL 表：`documents`、`document_chunks`
- Day 3 上传文件后写入 `documents`
- Day 3 PDF / Markdown 解析
- Day 3 文本切分并写入 `document_chunks`
- Day 3 前端解析按钮和 chunk 结果预览

暂未实现：

- 向量化
- Qdrant 入库
- DeepSeek 或其他大模型
- RAG 问答
- RBAC
- MinIO
- Redis
- Celery
- Nginx

## Day 3 接口

- `POST /api/auth/login`
- `POST /api/documents/upload`
- `GET /api/documents`
- `POST /api/documents/{document_id}/parse`
- `GET /api/documents/{document_id}/chunks`

`GET /api/documents` 会返回文档 ID、文件名、文件大小、解析状态、chunk 数量和上传时间。

解析状态：

- `uploaded`: 已上传，未解析
- `parsing`: 正在解析
- `parsed`: 解析成功
- `failed`: 解析失败

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

解析接口示例：

```bash
curl -X POST http://localhost:8000/api/documents/1/parse
curl http://localhost:8000/api/documents/1/chunks
```

## Day 3 账号

- Username: `admin`
- Password: `admin123`
- Token: `day2-demo-token`
