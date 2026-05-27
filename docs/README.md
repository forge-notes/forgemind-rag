# Day 4 Notes

Day 4 adds chunk embedding, Qdrant storage, and basic vector search.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant

Included Day 4 features:

- MySQL embedding fields on `documents` and `document_chunks`
- Qdrant collection: `knowledge_chunks`
- Pluggable embedding service configured by `EMBEDDING_*`
- Demo `local_hash` embedding provider
- `POST /api/documents/{document_id}/embed`
- `POST /api/search`
- Frontend vectorization button and search result preview

Not included yet:

- RAG answer generation
- DeepSeek or any answer-generating LLM
- Chat UI
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
