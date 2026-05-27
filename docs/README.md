# Day 5 Notes

Day 5 adds single-turn RAG question answering.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant
- Ollama embedding model: `bge-m3:latest`
- Ollama chat model: `qwen2.5:7b`

Included Day 5 features:

- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_BASE`, `LLM_API_KEY`
- Ollama `/api/chat` call with `stream=false`
- RAG service that retrieves top-k chunks from Qdrant
- Prompt with source-only answering rules
- `POST /api/ask`
- Frontend knowledge-base Q&A panel
- Answer and source citation display

Not included:

- Multi-turn chat
- Q&A history
- Streaming output
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
