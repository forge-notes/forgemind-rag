import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse
from uuid import uuid4

import fitz
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


APP_NAME = "Enterprise Knowledge Agent"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_STAGE = os.getenv("APP_STAGE", "Day 3")
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
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LoginRequest(BaseModel):
    username: str
    password: str


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _file_type(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return "pdf"
    if extension in {".md", ".markdown"}:
        return "markdown"
    raise HTTPException(status_code=400, detail="Only PDF and Markdown files are supported.")


def _stored_filename(original_filename: str) -> str:
    safe_name = _safe_document_name(original_filename)
    extension = Path(safe_name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(safe_name).stem).strip("._")
    if not stem:
        stem = "document"
    return f"{stem}_{uuid4().hex[:12]}{extension}"


def _document_response(document: Document) -> dict[str, object]:
    return {
        "id": document.id,
        "filename": document.original_filename,
        "stored_filename": document.filename,
        "file_size": document.file_size,
        "parse_status": document.parse_status,
        "chunk_count": document.chunk_count,
        "uploaded_at": document.uploaded_at.isoformat(),
        "parsed_at": document.parsed_at.isoformat() if document.parsed_at else None,
    }


def _chunk_response(chunk: DocumentChunk) -> dict[str, object]:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "page_number": chunk.page_number,
        "char_count": chunk.char_count,
        "created_at": chunk.created_at.isoformat(),
    }


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(end - overlap, start + 1)

    return chunks


def _extract_markdown_chunks(file_path: Path) -> list[tuple[str, int | None]]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return [(chunk, None) for chunk in _split_text(text)]


def _extract_pdf_chunks(file_path: Path) -> list[tuple[str, int | None]]:
    chunks: list[tuple[str, int | None]] = []
    with fitz.open(file_path) as pdf:
        for page_index, page in enumerate(pdf, start=1):
            page_text = page.get_text("text")
            chunks.extend((chunk, page_index) for chunk in _split_text(page_text))
    return chunks


def _extract_chunks(document: Document) -> list[tuple[str, int | None]]:
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {document.file_path}")
    if document.file_type == "pdf":
        return _extract_pdf_chunks(file_path)
    if document.file_type == "markdown":
        return _extract_markdown_chunks(file_path)
    raise ValueError(f"Unsupported file type: {document.file_type}")


def _sync_existing_uploads() -> None:
    upload_root = _upload_root()
    with SessionLocal() as db:
        for file_path in sorted(upload_root.iterdir(), key=lambda item: item.name.lower()):
            if (
                not file_path.is_file()
                or file_path.name == ".gitkeep"
                or file_path.suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS
            ):
                continue

            exists = db.query(Document.id).filter(Document.filename == file_path.name).first()
            if exists:
                continue

            db.add(
                Document(
                    filename=file_path.name,
                    original_filename=file_path.name,
                    file_path=str(file_path),
                    file_type=_file_type(file_path.name),
                    file_size=file_path.stat().st_size,
                    parse_status="uploaded",
                    chunk_count=0,
                    uploaded_at=datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc),
                    parsed_at=None,
                )
            )
        db.commit()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Day 3 FastAPI service for parsing and chunking uploaded documents.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    _upload_root()
    Base.metadata.create_all(bind=engine)
    _sync_existing_uploads()


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
        "checked_at": _utc_now().isoformat(),
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
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    original_filename = _safe_document_name(file.filename or "")
    stored_filename = _stored_filename(original_filename)
    file_type = _file_type(original_filename)
    upload_root = _upload_root()
    destination = upload_root / stored_filename

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    document = Document(
        filename=stored_filename,
        original_filename=original_filename,
        file_path=str(destination),
        file_type=file_type,
        file_size=destination.stat().st_size,
        parse_status="uploaded",
        chunk_count=0,
        uploaded_at=_utc_now(),
        parsed_at=None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _document_response(document)


@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return {"documents": [_document_response(document) for document in documents]}


@app.post("/api/documents/{document_id}/parse")
def parse_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    document.parse_status = "parsing"
    document.chunk_count = 0
    document.parsed_at = None
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.commit()

    try:
        extracted_chunks = _extract_chunks(document)
        created_at = _utc_now()
        for index, (content, page_number) in enumerate(extracted_chunks):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    page_number=page_number,
                    char_count=len(content),
                    created_at=created_at,
                )
            )

        document.parse_status = "parsed"
        document.chunk_count = len(extracted_chunks)
        document.parsed_at = _utc_now()
        db.commit()
        db.refresh(document)
        return _document_response(document)
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.parse_status = "failed"
            document.chunk_count = 0
            document.parsed_at = None
            db.commit()
        raise HTTPException(status_code=500, detail=f"Parse failed: {exc}") from exc


@app.get("/api/documents/{document_id}/chunks")
def list_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    return {
        "document": _document_response(document),
        "chunks": [_chunk_response(chunk) for chunk in chunks],
    }
