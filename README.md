# Enterprise Knowledge Agent

企业知识代理项目，用于后续构建企业知识库、文档解析、向量检索、RAG 问答和权限控制能力。

当前仓库已完成 Day 4：向量化与 Qdrant 基础检索。

## 技术栈

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Database: MySQL 8
- Vector Database: Qdrant
- Deployment: Docker Compose
- PDF Parser: PyMuPDF
- Embedding: pluggable embedding service

## 启动方式

MacBook 只负责写代码和 Git 推送，不需要安装 Docker、MySQL、Python、Node.js 或 Qdrant。

i5 Ubuntu 服务器负责运行全部服务。服务器需要安装 Docker 和 Docker Compose，然后在项目根目录执行：

```bash
cp .env.example .env
docker compose up -d --build
```

如果已经有 Day 1/Day 2/Day 3 的 `.env`，请补齐 Day 4 的 `EMBEDDING_*` 配置，并确认：

```bash
APP_STAGE=Day 4
```

Day 4 默认使用 `EMBEDDING_PROVIDER=local_hash`，这是一个无需外部 API 的演示 embedding provider。后续可替换为 `openai_compatible` 并配置真实 embedding API。

## 常用访问地址

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- Backend API docs: http://localhost:8000/docs
- Documents API: http://localhost:8000/api/documents
- Search API: http://localhost:8000/api/search
- Qdrant API: http://localhost:6333
- Qdrant dashboard: http://localhost:6333/dashboard

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
- `frontend`: React + Vite + TypeScript，提供登录、上传、解析、向量化和检索测试

`uploads/` 会挂载到后端容器的 `/app/uploads`。

## 当前进度

已完成：

- Day 1 工程初始化和 Docker Compose 可运行底座
- Day 2 简单登录、PDF/Markdown 上传、uploads 文件列表展示
- Day 3 MySQL 表：`documents`、`document_chunks`
- Day 3 PDF / Markdown 解析和文本切分
- Day 4 MySQL 字段：`embedding_status`、`embedded_at`、`vector_id`
- Day 4 Qdrant collection：`knowledge_chunks`
- Day 4 chunk embedding、Qdrant 入库、基础相似检索
- Day 4 前端向量化按钮和知识库检索测试区

暂未实现：

- DeepSeek 或其他大模型生成答案
- RAG 问答
- 聊天页面
- RBAC
- MinIO
- Redis
- Celery
- Nginx

## Day 4 接口

- `POST /api/auth/login`
- `POST /api/documents/upload`
- `GET /api/documents`
- `POST /api/documents/{document_id}/parse`
- `GET /api/documents/{document_id}/chunks`
- `POST /api/documents/{document_id}/embed`
- `POST /api/search`

`POST /api/documents/{document_id}/embed` 会读取文档 chunks，生成 embedding，写入 Qdrant 的 `knowledge_chunks` collection，并更新 MySQL embedding 状态。

`POST /api/search` 只返回相关 chunks，不生成最终答案。

## Embedding 配置

```env
EMBEDDING_PROVIDER=local_hash
EMBEDDING_MODEL=local-hash-demo
EMBEDDING_API_BASE=
EMBEDDING_API_KEY=
EMBEDDING_DIM=384
```

如果改为外部 OpenAI-compatible embedding 服务：

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_API_BASE=https://your-api.example.com/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_DIM=1024
```

如果 embedding 配置缺失或维度与 Qdrant collection 不一致，后端会返回清晰错误。

## 验证命令

```bash
curl http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/documents/1/parse
curl -X POST http://localhost:8000/api/documents/1/embed
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"你的问题","top_k":5}'
```

## 演示账号

- Username: `admin`
- Password: `admin123`
- Token: `day2-demo-token`
