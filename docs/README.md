# Day 3 Notes

Day 3 adds document parsing and text chunking on top of the existing login and upload flow.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant

Included Day 3 features:

- MySQL tables: `documents` and `document_chunks`
- Demo login with `admin` / `admin123`
- PDF and Markdown upload to `/app/uploads`
- PDF parsing with PyMuPDF
- Markdown parsing by reading text content
- Simple 900-character chunking with 120-character overlap
- Frontend parse action and chunk preview

Not included yet:

- Vectorization
- Qdrant document writes
- DeepSeek or any LLM
- RAG
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
