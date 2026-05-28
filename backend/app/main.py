import hashlib
import json
import logging
import math
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse
from uuid import uuid4

import fitz
import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


APP_NAME = "ForgeMind RAG"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_STAGE = os.getenv("APP_STAGE", "Day 6")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://eka_user:eka_password@mysql:3306/enterprise_knowledge_agent",
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = "knowledge_chunks"
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admin123"
DEMO_TOKEN = "day2-demo-token"
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".md", ".markdown"}
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

logger = logging.getLogger(__name__)


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
    embedding_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QARecord(Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class EmbeddingConfigError(ValueError):
    pass


class LLMConfigError(ValueError):
    pass


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
        self.model = os.getenv("EMBEDDING_MODEL", "").strip()
        self.api_base = os.getenv("EMBEDDING_API_BASE", "").strip().rstrip("/")
        self.api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
        self.dim = self._read_dimension()

    def _read_dimension(self) -> int:
        value = os.getenv("EMBEDDING_DIM", "").strip()
        if not value:
            return 0
        try:
            dimension = int(value)
        except ValueError as exc:
            raise EmbeddingConfigError("EMBEDDING_DIM must be an integer.") from exc
        if dimension <= 0:
            raise EmbeddingConfigError("EMBEDDING_DIM must be greater than 0.")
        return dimension

    def validate(self) -> None:
        if not self.provider:
            raise EmbeddingConfigError("EMBEDDING_PROVIDER is required.")
        if not self.dim:
            raise EmbeddingConfigError("EMBEDDING_DIM is required.")
        if self.provider in {"local_hash", "hash"}:
            return
        if self.provider == "ollama":
            missing = [
                name
                for name, value in {
                    "EMBEDDING_MODEL": self.model,
                    "EMBEDDING_API_BASE": self.api_base,
                }.items()
                if not value
            ]
            if missing:
                raise EmbeddingConfigError(
                    f"Missing embedding configuration: {', '.join(missing)}."
                )
            return
        if self.provider in {"openai", "openai_compatible"}:
            missing = [
                name
                for name, value in {
                    "EMBEDDING_MODEL": self.model,
                    "EMBEDDING_API_BASE": self.api_base,
                    "EMBEDDING_API_KEY": self.api_key,
                }.items()
                if not value
            ]
            if missing:
                raise EmbeddingConfigError(
                    f"Missing embedding configuration: {', '.join(missing)}."
                )
            return
        raise EmbeddingConfigError(
            "Unsupported EMBEDDING_PROVIDER. Use local_hash, ollama, or openai_compatible."
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.validate()
        if self.provider in {"local_hash", "hash"}:
            return [self._local_hash_embedding(text_value) for text_value in texts]
        if self.provider == "ollama":
            return self._ollama_embeddings(texts)
        return self._openai_compatible_embeddings(texts)

    def embed_text(self, text_value: str) -> list[float]:
        return self.embed_texts([text_value])[0]

    def _local_hash_embedding(self, text_value: str) -> list[float]:
        tokens = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text_value.lower())
        if not tokens:
            tokens = list(text_value.lower())

        vector = [0.0] * self.dim
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _ollama_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.api_base}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise RuntimeError("Ollama returned an unexpected number of vectors.")
        for embedding in embeddings:
            if len(embedding) != self.dim:
                raise RuntimeError(
                    f"Embedding dimension mismatch: expected {self.dim}, got {len(embedding)}."
                )
        return embeddings

    def _openai_compatible_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.api_base}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = [item["embedding"] for item in payload.get("data", [])]
        if len(embeddings) != len(texts):
            raise RuntimeError("Embedding API returned an unexpected number of vectors.")
        for embedding in embeddings:
            if len(embedding) != self.dim:
                raise RuntimeError(
                    f"Embedding dimension mismatch: expected {self.dim}, got {len(embedding)}."
                )
        return embeddings


class LLMService:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.model = os.getenv("LLM_MODEL", "").strip()
        self.api_base = os.getenv("LLM_API_BASE", "").strip().rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "").strip()

    def validate(self) -> None:
        if not self.provider:
            raise LLMConfigError("LLM_PROVIDER is required.")
        if self.provider != "ollama":
            raise LLMConfigError("Unsupported LLM_PROVIDER. Use ollama.")
        missing = [
            name
            for name, value in {
                "LLM_MODEL": self.model,
                "LLM_API_BASE": self.api_base,
            }.items()
            if not value
        ]
        if missing:
            raise LLMConfigError(f"Missing LLM configuration: {', '.join(missing)}.")

    def generate(self, prompt: str) -> str:
        self.validate()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = httpx.post(
                f"{self.api_base}/api/chat",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=180,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise RuntimeError(f"Ollama chat failed: HTTP {exc.response.status_code} {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama chat request failed: {exc}") from exc

        payload = response.json()
        answer = payload.get("message", {}).get("content", "")
        if not answer:
            raise RuntimeError("Ollama chat returned an empty answer.")
        return answer.strip()


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
qdrant_client = QdrantClient(url=QDRANT_URL, timeout=30)


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
        "embedding_status": document.embedding_status,
        "uploaded_at": document.uploaded_at.isoformat(),
        "parsed_at": document.parsed_at.isoformat() if document.parsed_at else None,
        "embedded_at": document.embedded_at.isoformat() if document.embedded_at else None,
    }


def _chunk_response(chunk: DocumentChunk) -> dict[str, object]:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "page_number": chunk.page_number,
        "char_count": chunk.char_count,
        "vector_id": chunk.vector_id,
        "embedding_status": chunk.embedding_status,
        "created_at": chunk.created_at.isoformat(),
        "embedded_at": chunk.embedded_at.isoformat() if chunk.embedded_at else None,
    }


def _qa_record_response(record: QARecord) -> dict[str, object]:
    try:
        sources = json.loads(record.sources_json)
    except (TypeError, json.JSONDecodeError):
        sources = []

    return {
        "id": record.id,
        "question": record.question,
        "answer": record.answer,
        "sources": sources,
        "model_name": record.model_name,
        "top_k": record.top_k,
        "created_at": record.created_at.isoformat(),
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


def _ensure_database_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    existing_documents = {column["name"] for column in inspector.get_columns("documents")}
    existing_chunks = {column["name"] for column in inspector.get_columns("document_chunks")}

    with engine.begin() as connection:
        if "embedding_status" not in existing_documents:
            connection.execute(
                text(
                    "ALTER TABLE documents "
                    "ADD COLUMN embedding_status VARCHAR(32) NOT NULL DEFAULT 'pending'"
                )
            )
        if "embedded_at" not in existing_documents:
            connection.execute(text("ALTER TABLE documents ADD COLUMN embedded_at DATETIME NULL"))
        if "vector_id" not in existing_chunks:
            connection.execute(text("ALTER TABLE document_chunks ADD COLUMN vector_id VARCHAR(128) NULL"))
        if "embedding_status" not in existing_chunks:
            connection.execute(
                text(
                    "ALTER TABLE document_chunks "
                    "ADD COLUMN embedding_status VARCHAR(32) NOT NULL DEFAULT 'pending'"
                )
            )
        if "embedded_at" not in existing_chunks:
            connection.execute(text("ALTER TABLE document_chunks ADD COLUMN embedded_at DATETIME NULL"))


def _embedding_service() -> EmbeddingService:
    return EmbeddingService()


def _embedding_error_response(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=f"Embedding configuration error: {exc}")


def _llm_error_response(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=f"LLM configuration error: {exc}")


def _ensure_qdrant_collection(embedding_service: EmbeddingService) -> None:
    embedding_service.validate()
    try:
        exists = qdrant_client.collection_exists(QDRANT_COLLECTION)
        if not exists:
            qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=models.VectorParams(
                    size=embedding_service.dim,
                    distance=models.Distance.COSINE,
                ),
            )
            return

        collection = qdrant_client.get_collection(QDRANT_COLLECTION)
        vectors_config = collection.config.params.vectors
        existing_size = getattr(vectors_config, "size", None)
        if isinstance(vectors_config, dict):
            first_vector = next(iter(vectors_config.values()))
            existing_size = getattr(first_vector, "size", None)
        if existing_size and existing_size != embedding_service.dim:
            raise EmbeddingConfigError(
                f"Qdrant collection dimension is {existing_size}, "
                f"but EMBEDDING_DIM is {embedding_service.dim}."
            )
    except EmbeddingConfigError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unable to prepare Qdrant collection: {exc}") from exc


def _qdrant_search(query_vector: list[float], top_k: int):
    if hasattr(qdrant_client, "search"):
        return qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    result = qdrant_client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return result.points


def _search_knowledge_chunks(query: str, top_k: int, include_chunk_id: bool = True) -> list[dict[str, object]]:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise HTTPException(status_code=400, detail="query is required.")
    safe_top_k = max(1, min(top_k, 20))

    try:
        embedding_service = _embedding_service()
        _ensure_qdrant_collection(embedding_service)
        query_vector = embedding_service.embed_text(cleaned_query)
        search_results = _qdrant_search(query_vector, safe_top_k)
    except EmbeddingConfigError as exc:
        raise _embedding_error_response(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    sources: list[dict[str, object]] = []
    for item in search_results:
        item_payload = item.payload or {}
        source = {
            "document_id": item_payload.get("document_id"),
            "filename": item_payload.get("filename"),
            "chunk_index": item_payload.get("chunk_index"),
            "page_number": item_payload.get("page_number"),
            "score": float(getattr(item, "score", 0.0)),
            "content": item_payload.get("content", ""),
        }
        if include_chunk_id:
            source["chunk_id"] = item_payload.get("chunk_id")
        sources.append(source)

    return sources


def _build_rag_context(sources: list[dict[str, object]]) -> str:
    if not sources:
        return "当前没有检索到参考资料。"

    blocks = []
    for index, source in enumerate(sources, start=1):
        page_number = source.get("page_number")
        page_text = f"第 {page_number} 页" if page_number else "页码未知"
        blocks.append(
            "\n".join(
                [
                    f"【资料 {index}】",
                    f"文档名：{source.get('filename')}",
                    f"页码：{page_text}",
                    f"chunk_index：{source.get('chunk_index')}",
                    f"相似度：{source.get('score')}",
                    "内容：",
                    str(source.get("content", "")),
                ]
            )
        )
    return "\n\n".join(blocks)


def _build_rag_prompt(question: str, context: str) -> str:
    return f"""你是一个企业知识库问答助手。

请只根据【参考资料】回答用户问题。
如果参考资料中没有答案，请明确说明“当前知识库中没有找到足够信息”。
不要编造不存在的信息。
回答要简洁、准确、结构清晰。

【参考资料】
{context}

【用户问题】
{question}

请基于参考资料回答："""


class RagService:
    def __init__(self) -> None:
        self.llm_service = LLMService()

    def ask(self, question: str, top_k: int) -> dict[str, object]:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise HTTPException(status_code=400, detail="question is required.")

        safe_top_k = max(1, min(top_k, 20))
        sources = _search_knowledge_chunks(cleaned_question, safe_top_k, include_chunk_id=False)
        context = _build_rag_context(sources)
        prompt = _build_rag_prompt(cleaned_question, context)
        answer = self.llm_service.generate(prompt)
        return {
            "answer": answer,
            "sources": sources,
            "model_name": self.llm_service.model,
            "top_k": safe_top_k,
        }


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
                    embedding_status="pending",
                    uploaded_at=datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc),
                    parsed_at=None,
                    embedded_at=None,
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
    description="Day 6 FastAPI service for RAG question answering with history.",
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
    _ensure_database_schema()
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
        embedding_status="pending",
        uploaded_at=_utc_now(),
        parsed_at=None,
        embedded_at=None,
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
    document.embedding_status = "pending"
    document.parsed_at = None
    document.embedded_at = None
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
                    vector_id=None,
                    embedding_status="pending",
                    created_at=created_at,
                    embedded_at=None,
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
            document.embedding_status = "pending"
            document.parsed_at = None
            document.embedded_at = None
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


@app.post("/api/documents/{document_id}/embed")
def embed_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.parse_status != "parsed":
        raise HTTPException(status_code=400, detail="Please parse the document before embedding.")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks found for this document.")

    try:
        embedding_service = _embedding_service()
        _ensure_qdrant_collection(embedding_service)
    except EmbeddingConfigError as exc:
        raise _embedding_error_response(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    document.embedding_status = "embedding"
    document.embedded_at = None
    for chunk in chunks:
        chunk.embedding_status = "embedding"
        chunk.embedded_at = None
    db.commit()

    try:
        embeddings = embedding_service.embed_texts([chunk.content for chunk in chunks])
        embedded_at = _utc_now()
        points: list[models.PointStruct] = []

        for chunk, embedding in zip(chunks, embeddings):
            vector_id = chunk.vector_id or str(uuid4())
            chunk.vector_id = vector_id
            chunk.embedding_status = "embedded"
            chunk.embedded_at = embedded_at
            points.append(
                models.PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload={
                        "document_id": document.id,
                        "chunk_id": chunk.id,
                        "filename": document.original_filename,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "content": chunk.content,
                    },
                )
            )

        qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        document.embedding_status = "embedded"
        document.embedded_at = embedded_at
        db.commit()
        db.refresh(document)
        return _document_response(document)
    except EmbeddingConfigError as exc:
        db.rollback()
        raise _embedding_error_response(exc) from exc
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.embedding_status = "failed"
            document.embedded_at = None
            (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document.id)
                .update({"embedding_status": "failed", "embedded_at": None})
            )
            db.commit()
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc


@app.post("/api/search")
def search_chunks(payload: SearchRequest) -> dict[str, object]:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required.")
    top_k = max(1, min(payload.top_k, 20))

    results = _search_knowledge_chunks(query, top_k)

    return {"query": query, "top_k": top_k, "results": results}


@app.post("/api/ask")
def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        result = RagService().ask(payload.question, payload.top_k)
    except LLMConfigError as exc:
        raise _llm_error_response(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG answer failed: {exc}") from exc

    record_id: int | None = None
    try:
        record = QARecord(
            question=payload.question.strip(),
            answer=str(result["answer"]),
            sources_json=json.dumps(result["sources"], ensure_ascii=False),
            model_name=str(result["model_name"]),
            top_k=int(result["top_k"]),
            created_at=_utc_now(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    except Exception:
        db.rollback()
        logger.exception("Failed to save QA record.")

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "record_id": record_id,
    }


@app.get("/api/qa/history")
def list_qa_history(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    records = db.query(QARecord).order_by(QARecord.created_at.desc()).limit(20).all()
    return {"records": [_qa_record_response(record) for record in records]}
