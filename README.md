# Enterprise Knowledge Agent

企业知识代理项目，用于构建企业知识库、文档解析、向量检索、RAG 问答和权限控制能力。

当前仓库已完成 Day 5：RAG 问答。

## 技术栈

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Database: MySQL 8
- Vector Database: Qdrant
- Deployment: Docker Compose
- PDF Parser: PyMuPDF
- Embedding: Ollama `bge-m3:latest`
- LLM: Ollama `qwen2.5:7b`

## 启动方式

MacBook 只负责写代码和 Git 推送，不需要安装 Docker、MySQL、Python、Node.js、Qdrant 或 Ollama。

i5 Ubuntu 服务器负责运行 Docker Compose 服务。Ollama 可以在局域网其他机器运行，API 地址通过 `.env` 配置。

```bash
cp .env.example .env
docker compose up -d --build
```

如果已经有旧 `.env`，请补齐 Day 5 配置，并确认：

```env
APP_STAGE=Day 5
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_API_BASE=http://192.168.9.39:11434
EMBEDDING_DIM=1024
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
LLM_API_BASE=http://192.168.9.39:11434
```

`bge-m3` 只用于 embedding，`qwen2.5` 用于生成最终回答。

## 常用访问地址

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- Backend API docs: http://localhost:8000/docs
- Documents API: http://localhost:8000/api/documents
- Search API: http://localhost:8000/api/search
- Ask API: http://localhost:8000/api/ask
- Qdrant dashboard: http://localhost:6333/dashboard

如果在局域网访问 i5 Ubuntu 服务器，请把 `localhost` 替换为服务器 IP。

## 当前进度

已完成：

- Day 1 工程初始化和 Docker Compose 可运行底座
- Day 2 简单登录、PDF/Markdown 上传、uploads 文件列表展示
- Day 3 PDF / Markdown 解析和文本切分
- Day 4 chunk embedding、Qdrant 入库、基础相似检索
- Day 5 基于检索 chunks 的 RAG 问答
- Day 5 前端知识库问答区域和来源引用展示

暂未实现：

- 多轮聊天
- 问答历史保存
- 流式输出
- RBAC
- MinIO
- Redis
- Celery
- Nginx

## Day 5 接口

- `POST /api/auth/login`
- `POST /api/documents/upload`
- `GET /api/documents`
- `POST /api/documents/{document_id}/parse`
- `GET /api/documents/{document_id}/chunks`
- `POST /api/documents/{document_id}/embed`
- `POST /api/search`
- `POST /api/ask`

`POST /api/ask` 请求：

```json
{
  "question": "问题内容",
  "top_k": 5
}
```

响应包含：

- `answer`: Ollama 聊天模型基于参考资料生成的回答
- `sources`: Qdrant 检索到的来源 chunks

Prompt 约束：

- 只根据参考资料回答
- 资料不足时说明“当前知识库中没有找到足够信息”
- 不编造
- 回答简洁、准确、结构清晰

## 验证命令

```bash
curl http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/documents/1/parse
curl -X POST http://localhost:8000/api/documents/1/embed
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"你的问题","top_k":5}'
```

## 演示账号

- Username: `admin`
- Password: `admin123`
- Token: `day2-demo-token`
