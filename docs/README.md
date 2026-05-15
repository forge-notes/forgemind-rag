# Day 1 Notes

Day 1 only initializes the project structure and Docker Compose runtime base.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant

Not included yet:

- Login
- File upload workflow
- RAG
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
