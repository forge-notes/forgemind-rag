# Day 6 Notes

Day 6 adds Q&A history storage and a cleaner demo experience for single-turn RAG.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant
- Ollama embedding model: `bge-m3:latest`
- Ollama chat model: `qwen2.5:7b`

Included Day 6 features:

- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_BASE`, `LLM_API_KEY`
- Ollama `/api/chat` call with `stream=false`
- RAG service that retrieves top-k chunks from Qdrant
- Prompt with source-only answering rules
- `POST /api/ask`
- `qa_records` table for Q&A records
- `GET /api/qa/history` for the latest 20 records
- Frontend knowledge-base Q&A panel with loading and error states
- Example question buttons
- History list that can reload an answer and its sources
- Source citation cards with concise previews

Not included:

- Multi-turn chat
- Streaming output
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
