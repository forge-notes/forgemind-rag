# Day 2 Notes

Day 2 adds the smallest usable login and document upload flow on top of the Docker Compose runtime base.

Included services:

- FastAPI backend
- React + Vite + TypeScript frontend
- MySQL 8
- Qdrant

Included Day 2 features:

- Demo login with `admin` / `admin123`
- PDF and Markdown upload to `/app/uploads`
- Document listing from the mounted `uploads/` directory

Not included yet:

- RAG
- RBAC
- MinIO
- Redis
- Celery
- Nginx

The `uploads/` directory is mounted into the backend container at `/app/uploads`.
