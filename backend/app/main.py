import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


APP_NAME = "Enterprise Knowledge Agent"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_STAGE = os.getenv("APP_STAGE", "Day 1")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://eka_user:eka_password@mysql:3306/enterprise_knowledge_agent",
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]


def _database_service_name() -> str:
    return urlparse(DATABASE_URL).hostname or "mysql"


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Day 1 FastAPI service for the Enterprise Knowledge Agent project.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
        "stage": APP_STAGE,
        "version": APP_VERSION,
    }


@app.get("/api/health")
def api_health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "backend",
        "project": APP_NAME,
        "stage": APP_STAGE,
        "version": APP_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "database_service": _database_service_name(),
            "qdrant_url": QDRANT_URL,
            "upload_dir": UPLOAD_DIR,
        },
    }


@app.get("/api/version")
def api_version() -> dict[str, str]:
    return {
        "project": APP_NAME,
        "service": "backend",
        "stage": APP_STAGE,
        "version": APP_VERSION,
    }
