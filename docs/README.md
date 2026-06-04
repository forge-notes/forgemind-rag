# Documentation Index

Day 7 focuses on deployment presentation and portfolio packaging. Business features remain at the Day 6 scope: upload, parse, chunk, embed, search, RAG answer, source citation, and Q&A history.

## Documents

- [Demo Script](demo-script.md): step-by-step demo flow for interviews and project walkthroughs.
- [Architecture](architecture.md): system components, data flow, RAG flow, and data tables.
- [Testing Questions](testing-questions.md): example questions for validating retrieval and answer quality.

## Included Services

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant
- Ollama embedding model: `bge-m3:latest`
- Chat model: Ollama `qwen2.5:7b`, DeepSeek API, or another OpenAI-compatible model

## Current Scope

Included:

- Document upload
- PDF / Markdown parsing
- Text chunking
- Ollama embedding
- Qdrant vector search
- RAG question answering
- Source citations
- Q&A history
- Docker Compose deployment base
- GitHub README and interview demo documentation

Not included:

- Multi-turn chat
- Streaming output
- RBAC
- Multi-tenancy
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
