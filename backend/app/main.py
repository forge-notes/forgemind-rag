import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


APP_NAME = "Enterprise Knowledge Agent"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_STAGE = os.getenv("APP_STAGE", "Day 2")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://eka_user:eka_password@mysql:3306/enterprise_knowledge_agent",
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admin123"
DEMO_TOKEN = "day2-demo-token"
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".md", ".markdown"}


class LoginRequest(BaseModel):
    username: str
    password: str


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]


def _database_service_name() -> str:
    return urlparse(DATABASE_URL).hostname or "mysql"


def _upload_root() -> Path:
    upload_root = Path(UPLOAD_DIR)
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root


def _safe_document_name(filename: str) -> str:
    safe_name = Path(filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Filename is required.")
    if Path(safe_name).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Markdown files are supported.",
        )
    return safe_name


def _document_response(file_path: Path) -> dict[str, object]:
    stat = file_path.stat()
    return {
        "filename": file_path.name,
        "file_size": stat.st_size,
        "uploaded_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Day 2 FastAPI service for the Enterprise Knowledge Agent project.",
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


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict[str, str]:
    if payload.username != DEMO_USERNAME or payload.password != DEMO_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return {
        "token": DEMO_TOKEN,
        "token_type": "demo",
        "username": payload.username,
    }


@app.post("/api/documents/upload")
def upload_document(file: UploadFile = File(...)) -> dict[str, object]:
    safe_name = _safe_document_name(file.filename or "")
    upload_root = _upload_root()
    destination = upload_root / safe_name

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    return _document_response(destination)


@app.get("/api/documents")
def list_documents() -> dict[str, list[dict[str, object]]]:
    upload_root = _upload_root()
    documents = [
        _document_response(file_path)
        for file_path in sorted(upload_root.iterdir(), key=lambda item: item.name.lower())
        if file_path.is_file()
        and file_path.name != ".gitkeep"
        and file_path.suffix.lower() in ALLOWED_DOCUMENT_EXTENSIONS
    ]

    return {"documents": documents}
