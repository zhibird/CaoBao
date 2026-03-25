from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chunk_embedding import ChunkEmbedding
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.team import Team
from app.schemas.document import DocumentImportRequest
from app.services.chunk_service import ChunkSection, ChunkService
from app.services.retrieval_service import RetrievalService

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Image = None

try:
    import pytesseract  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None


@dataclass(frozen=True)
class ParseResult:
    text: str
    sections: list[ChunkSection]
    page_count: int | None
    meta: dict[str, object]


@dataclass(frozen=True)
class PipelineError:
    stage: str
    code: str
    message: str


class DocumentService:
    _ALLOWED_TYPES = {"txt", "md", "pdf", "png", "jpg", "jpeg", "webp"}
    _IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
    _MIME_BY_TYPE = {
        "txt": "text/plain",
        "md": "text/markdown",
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    _MIME_ALIASES = {
        "txt": {"text/plain"},
        "md": {"text/markdown", "text/plain"},
        "pdf": {"application/pdf"},
        "png": {"image/png"},
        "jpg": {"image/jpeg", "image/jpg"},
        "jpeg": {"image/jpeg", "image/jpg"},
        "webp": {"image/webp"},
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.upload_root = self._resolve_upload_root()

    def import_document(self, payload: DocumentImportRequest) -> Document:
        self._ensure_team_and_conversation(
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
        )

        now = datetime.now(timezone.utc)
        content = payload.content.strip()
        size_bytes = len(content.encode("utf-8"))
        if size_bytes <= 0:
            raise DomainValidationError("EMPTY_FILE: imported text content cannot be empty.")

        document = Document(
            document_id=str(uuid4()),
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            source_name=payload.source_name,
            content_type=payload.content_type,
            mime_type=self._MIME_BY_TYPE[payload.content_type],
            size_bytes=size_bytes,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            storage_key=f"inline://import/{uuid4()}",
            status="uploaded",
            content=content,
            created_at=now,
            updated_at=now,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def upload_document(
        self,
        *,
        team_id: str,
        conversation_id: str | None,
        source_name: str,
        declared_mime_type: str | None,
        file_bytes: bytes,
    ) -> Document:
        self._ensure_team_and_conversation(team_id=team_id, conversation_id=conversation_id)
        if not file_bytes:
            raise DomainValidationError("EMPTY_FILE: uploaded file is empty.")

        max_size = max(1, int(self.settings.upload_max_file_size_mb)) * 1024 * 1024
        if len(file_bytes) > max_size:
            raise DomainValidationError(
                f"FILE_TOO_LARGE: file exceeds {self.settings.upload_max_file_size_mb} MB limit."
            )

        content_type = self._detect_content_type(source_name=source_name)
        mime_type = self._sniff_mime(content_type=content_type, file_bytes=file_bytes)
        self._validate_declared_mime(
            content_type=content_type,
            declared_mime_type=declared_mime_type,
            sniffed_mime_type=mime_type,
        )

        document_id = str(uuid4())
        storage_key = self._build_storage_key(
            team_id=team_id,
            document_id=document_id,
            source_name=source_name,
        )
        self._write_file(storage_key=storage_key, file_bytes=file_bytes)

        now = datetime.now(timezone.utc)
        document = Document(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
            source_name=source_name,
            content_type=content_type,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            sha256=hashlib.sha256(file_bytes).hexdigest(),
            storage_key=storage_key,
            status="uploaded",
            content="",
            created_at=now,
            updated_at=now,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def process_document_pipeline(
        self,
        *,
        document_id: str,
        team_id: str,
        conversation_id: str | None,
        user_id: str | None,
        auto_index: bool,
        embedding_model: str | None,
        chunk_service: ChunkService,
        retrieval_service: RetrievalService,
        max_chars: int = 600,
        overlap: int = 80,
    ) -> None:
        document = self.get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )
        self._clear_failure(document)

        parse_result, parse_error = self._parse_phase(document)
        if parse_error is not None:
            self._mark_failed(document=document, error=parse_error)
            return

        _, chunk_error = self._chunk_phase(
            document=document,
            team_id=team_id,
            conversation_id=conversation_id,
            max_chars=max_chars,
            overlap=overlap,
            sections=parse_result.sections if parse_result is not None else None,
            chunk_service=chunk_service,
        )
        if chunk_error is not None:
            self._mark_failed(document=document, error=chunk_error)
            return

        if not auto_index:
            return

        index_error = self._index_phase(
            team_id=team_id,
            user_id=user_id,
            conversation_id=conversation_id,
            document_id=document_id,
            embedding_model=embedding_model,
            retrieval_service=retrieval_service,
        )
        if index_error is not None:
            document = self.get_document_in_team(
                document_id=document_id,
                team_id=team_id,
                conversation_id=conversation_id,
            )
            self._mark_failed(document=document, error=index_error)

    def list_documents(
        self,
        team_id: str,
        conversation_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Document]:
        stmt = select(Document).where(Document.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        if status is not None:
            stmt = stmt.where(Document.status == status.strip().lower())
        stmt = stmt.order_by(Document.created_at.desc())
        stmt = stmt.limit(max(1, min(limit, 200)))
        return list(self.db.scalars(stmt).all())

    def get_documents_in_scope(
        self,
        *,
        team_id: str,
        conversation_id: str | None,
        document_ids: list[str] | None = None,
        ready_only: bool = True,
        limit: int = 200,
    ) -> list[Document]:
        if document_ids:
            ordered: list[Document] = []
            for document_id in document_ids:
                try:
                    item = self.get_document_in_team(
                        document_id=document_id,
                        team_id=team_id,
                        conversation_id=conversation_id,
                    )
                except EntityNotFoundError:
                    continue
                if ready_only and item.status != "ready":
                    continue
                ordered.append(item)
            return ordered

        if conversation_id is None:
            return []

        items = self.list_documents(
            team_id=team_id,
            conversation_id=conversation_id,
            status="ready" if ready_only else None,
            limit=limit,
        )
        if ready_only:
            return [item for item in items if item.status == "ready"]
        return items

    def build_chat_image_attachments(
        self,
        *,
        documents: list[Document],
    ) -> list[dict[str, str]]:
        attachments: list[dict[str, str]] = []
        for item in documents:
            if item.content_type not in self._IMAGE_TYPES:
                continue
            if item.storage_key.startswith("inline://"):
                continue
            path = self.upload_root / item.storage_key
            if not path.exists() or not path.is_file():
                continue
            file_bytes = path.read_bytes()
            data_url = self._to_data_url(mime_type=item.mime_type, file_bytes=file_bytes)
            attachments.append(
                {
                    "document_id": item.document_id,
                    "source_name": item.source_name,
                    "mime_type": item.mime_type,
                    "data_url": data_url,
                }
            )
        return attachments

    def get_document_in_team(
        self,
        document_id: str,
        team_id: str,
        conversation_id: str | None = None,
    ) -> Document:
        stmt = select(Document).where(
            Document.document_id == document_id,
            Document.team_id == team_id,
        )
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        document = self.db.scalar(stmt)
        if document is None:
            raise EntityNotFoundError(f"Document '{document_id}' not found in team '{team_id}'.")
        return document

    def update_document_status(
        self,
        *,
        document_id: str,
        team_id: str,
        status: str,
        conversation_id: str | None = None,
    ) -> Document:
        document = self.get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )
        document.status = status
        document.updated_at = datetime.now(timezone.utc)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def resolve_original_file(
        self,
        *,
        document_id: str,
        team_id: str,
        conversation_id: str | None,
    ) -> tuple[Path, Document]:
        document = self.get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )
        if document.storage_key.startswith("inline://"):
            raise EntityNotFoundError(f"Document '{document_id}' has no uploaded original file.")
        path = self.upload_root / document.storage_key
        if not path.exists() or not path.is_file():
            raise EntityNotFoundError(f"Original file for document '{document_id}' was not found.")
        return path, document

    def delete_document(
        self,
        *,
        document_id: str,
        team_id: str,
        conversation_id: str | None = None,
    ) -> None:
        document = self.get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )

        self._best_effort_delete_file(document)
        self.db.execute(
            delete(ChunkEmbedding).where(
                ChunkEmbedding.document_id == document_id,
                ChunkEmbedding.team_id == team_id,
            )
        )
        self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.team_id == team_id,
            )
        )
        self.db.execute(
            delete(Document).where(
                Document.document_id == document_id,
                Document.team_id == team_id,
            )
        )
        self.db.commit()

    def _parse_phase(self, document: Document) -> tuple[ParseResult | None, PipelineError | None]:
        self._set_status(document, "parsing")
        try:
            parse_result = self._parse_document(document)
        except DomainValidationError as exc:
            return None, self._to_pipeline_error(stage="parse", exc=exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            return None, PipelineError(stage="parse", code="PARSE_FAILED", message=str(exc))

        if not parse_result.text.strip():
            return None, PipelineError(
                stage="parse",
                code="NO_TEXT_EXTRACTED",
                message="No text could be extracted from the uploaded file.",
            )

        document.content = parse_result.text
        document.page_count = parse_result.page_count
        document.meta_json = json.dumps(parse_result.meta, separators=(",", ":")) if parse_result.meta else None
        document.failure_stage = None
        document.error_code = None
        document.error_message = None
        self._set_status(document, "uploaded")
        return parse_result, None

    def _chunk_phase(
        self,
        *,
        document: Document,
        team_id: str,
        conversation_id: str | None,
        max_chars: int,
        overlap: int,
        sections: list[ChunkSection] | None,
        chunk_service: ChunkService,
    ) -> tuple[list[DocumentChunk] | None, PipelineError | None]:
        try:
            chunks = chunk_service.chunk_document(
                document_id=document.document_id,
                team_id=team_id,
                conversation_id=conversation_id,
                max_chars=max_chars,
                overlap=overlap,
                sections=sections,
            )
            return chunks, None
        except DomainValidationError as exc:
            return None, self._to_pipeline_error(stage="chunk", exc=exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            return None, PipelineError(stage="chunk", code="CHUNK_FAILED", message=str(exc))

    def _index_phase(
        self,
        *,
        team_id: str,
        user_id: str | None,
        conversation_id: str | None,
        document_id: str,
        embedding_model: str | None,
        retrieval_service: RetrievalService,
    ) -> PipelineError | None:
        try:
            retrieval_service.index_chunks(
                team_id=team_id,
                user_id=user_id,
                document_ids=[document_id],
                conversation_id=conversation_id,
                embedding_model=embedding_model,
                rebuild=True,
            )
            return None
        except DomainValidationError as exc:
            return self._to_pipeline_error(stage="index", exc=exc)
        except EntityNotFoundError as exc:
            return PipelineError(stage="index", code="INDEX_FAILED", message=str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            return PipelineError(stage="index", code="INDEX_FAILED", message=str(exc))

    def _mark_failed(self, *, document: Document, error: PipelineError) -> None:
        document.status = "failed"
        document.failure_stage = error.stage
        document.error_code = error.code
        document.error_message = error.message
        document.updated_at = datetime.now(timezone.utc)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

    def _clear_failure(self, document: Document) -> None:
        document.failure_stage = None
        document.error_code = None
        document.error_message = None
        document.updated_at = datetime.now(timezone.utc)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

    def _set_status(self, document: Document, status: str) -> None:
        document.status = status
        document.updated_at = datetime.now(timezone.utc)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

    def _parse_document(self, document: Document) -> ParseResult:
        if document.storage_key.startswith("inline://"):
            sections = [ChunkSection(text=document.content)]
            return ParseResult(
                text=document.content,
                sections=sections,
                page_count=None,
                meta={"inline": True},
            )

        path = self.upload_root / document.storage_key
        if not path.exists() or not path.is_file():
            raise DomainValidationError("PARSE_FAILED: original uploaded file does not exist.")
        file_bytes = path.read_bytes()

        if document.content_type in {"txt", "md"}:
            return self._parse_text_file(document=document, file_bytes=file_bytes)
        if document.content_type == "pdf":
            return self._parse_pdf_file(document=document, file_bytes=file_bytes)
        if document.content_type in {"png", "jpg", "jpeg", "webp"}:
            return self._parse_image_file(document=document, file_bytes=file_bytes)
        raise DomainValidationError("UNSUPPORTED_FILE_TYPE: unsupported document type.")

    def _parse_text_file(self, *, document: Document, file_bytes: bytes) -> ParseResult:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DomainValidationError("UNSUPPORTED_TEXT_ENCODING: only UTF-8 text is supported.") from exc
        normalized = text.strip()
        return ParseResult(
            text=normalized,
            sections=[ChunkSection(text=normalized)] if normalized else [],
            page_count=None,
            meta={"mime_type": document.mime_type, "ocr_used": False},
        )

    def _parse_pdf_file(self, *, document: Document, file_bytes: bytes) -> ParseResult:
        reader = PdfReader(BytesIO(file_bytes))
        page_count = len(reader.pages)
        sections: list[ChunkSection] = []
        merged_parts: list[str] = []

        for index, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue
            if merged_parts:
                merged_parts.append("\n\n")
            merged_parts.append(page_text)
            sections.append(
                ChunkSection(
                    text=page_text,
                    page_no=index,
                    locator_label=f"Page {index}",
                    block_type="paragraph",
                )
            )

        text = "".join(merged_parts)
        if not text:
            text = f"PDF attachment: {document.source_name}"
            sections = [
                ChunkSection(
                    text=text,
                    page_no=1 if page_count else None,
                    locator_label="Page 1" if page_count else None,
                    block_type="paragraph",
                )
            ]
        meta = {"mime_type": "application/pdf", "ocr_used": False}
        return ParseResult(text=text, sections=sections, page_count=page_count, meta=meta)

    def _parse_image_file(self, *, document: Document, file_bytes: bytes) -> ParseResult:
        width = None
        height = None
        text = ""
        ocr_used = False

        if Image is not None:
            with Image.open(BytesIO(file_bytes)) as img:
                width, height = img.size
                if pytesseract is not None:
                    try:
                        text = (pytesseract.image_to_string(img) or "").strip()
                        ocr_used = bool(text)
                    except Exception:
                        text = ""
                        ocr_used = False

        if not text:
            text = f"Image attachment: {document.source_name}"

        return ParseResult(
            text=text,
            sections=[
                ChunkSection(
                    text=text,
                    page_no=1,
                    locator_label="Page 1",
                    block_type="ocr",
                )
            ],
            page_count=1,
            meta={
                "mime_type": document.mime_type,
                "ocr_used": ocr_used,
                "ocr_engine": "pytesseract" if ocr_used else "none",
                "width": width,
                "height": height,
            },
        )

    def _ensure_team_and_conversation(self, *, team_id: str, conversation_id: str | None) -> None:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' does not exist.")

        if conversation_id is None:
            return

        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None:
            raise EntityNotFoundError(f"Conversation '{conversation_id}' does not exist.")
        if conversation.team_id != team_id:
            raise EntityNotFoundError(
                f"Conversation '{conversation_id}' does not belong to team '{team_id}'."
            )

    def _detect_content_type(self, *, source_name: str) -> str:
        normalized = source_name.strip()
        if not normalized:
            raise DomainValidationError("UNSUPPORTED_FILE_TYPE: file name is required.")
        suffix = Path(normalized).suffix.lower().lstrip(".")
        if suffix not in self._ALLOWED_TYPES:
            raise DomainValidationError("UNSUPPORTED_FILE_TYPE: only txt/md/pdf/png/jpg/jpeg/webp are supported.")
        return suffix

    def _sniff_mime(self, *, content_type: str, file_bytes: bytes) -> str:
        if content_type in {"txt", "md"}:
            if b"\x00" in file_bytes:
                raise DomainValidationError("UNSUPPORTED_TEXT_ENCODING: binary data detected for text file.")
            try:
                file_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise DomainValidationError("UNSUPPORTED_TEXT_ENCODING: only UTF-8 text is supported.") from exc
            return self._MIME_BY_TYPE[content_type]

        if content_type == "pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise DomainValidationError("UNSUPPORTED_FILE_TYPE: file bytes are not a valid PDF signature.")
            return "application/pdf"

        if content_type == "png":
            if file_bytes[:8] != b"\x89PNG\r\n\x1a\n":
                raise DomainValidationError("UNSUPPORTED_FILE_TYPE: file bytes are not a valid PNG signature.")
            return "image/png"

        if content_type in {"jpg", "jpeg"}:
            if not file_bytes.startswith(b"\xff\xd8\xff"):
                raise DomainValidationError("UNSUPPORTED_FILE_TYPE: file bytes are not a valid JPEG signature.")
            return "image/jpeg"

        if content_type == "webp":
            if len(file_bytes) < 12 or file_bytes[:4] != b"RIFF" or file_bytes[8:12] != b"WEBP":
                raise DomainValidationError("UNSUPPORTED_FILE_TYPE: file bytes are not a valid WEBP signature.")
            return "image/webp"

        raise DomainValidationError("UNSUPPORTED_FILE_TYPE: unsupported file type.")

    def _validate_declared_mime(
        self,
        *,
        content_type: str,
        declared_mime_type: str | None,
        sniffed_mime_type: str,
    ) -> None:
        declared = str(declared_mime_type or "").split(";", 1)[0].strip().lower()
        if not declared or declared == "application/octet-stream":
            return
        allowed = set(self._MIME_ALIASES.get(content_type, set()))
        allowed.add(sniffed_mime_type)
        if declared not in allowed:
            raise DomainValidationError(
                f"UNSUPPORTED_FILE_TYPE: MIME mismatch (declared={declared}, detected={sniffed_mime_type})."
            )

    def _resolve_upload_root(self) -> Path:
        configured = Path(self.settings.upload_root_dir)
        if not configured.is_absolute():
            configured = PROJECT_ROOT / configured
        configured.mkdir(parents=True, exist_ok=True)
        return configured

    def _build_storage_key(self, *, team_id: str, document_id: str, source_name: str) -> str:
        safe_name = self._sanitize_file_name(source_name)
        return f"{team_id}/{document_id}/original/{safe_name}"

    def _sanitize_file_name(self, source_name: str) -> str:
        base_name = Path(source_name).name.strip()
        if not base_name:
            base_name = "uploaded"
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")
        if not normalized:
            normalized = f"uploaded_{uuid4().hex[:8]}"
        return normalized[:255]

    def _write_file(self, *, storage_key: str, file_bytes: bytes) -> None:
        target = self.upload_root / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)

    def _to_data_url(self, *, mime_type: str, file_bytes: bytes) -> str:
        encoded = base64.b64encode(file_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _best_effort_delete_file(self, document: Document) -> None:
        if document.storage_key.startswith("inline://"):
            return
        target = self.upload_root / document.storage_key
        try:
            if target.exists() and target.is_file():
                target.unlink()
            document_root = target.parent.parent if target.parent.name == "original" else target.parent
            if document_root.exists():
                for child in sorted(document_root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                    else:
                        child.rmdir()
                document_root.rmdir()
        except OSError:
            # Best effort cleanup only.
            return

    def _to_pipeline_error(self, *, stage: str, exc: DomainValidationError) -> PipelineError:
        message = str(exc)
        code = self._extract_error_code(message)
        fallback_code = {"parse": "PARSE_FAILED", "chunk": "CHUNK_FAILED", "index": "INDEX_FAILED"}.get(
            stage, "PARSE_FAILED"
        )
        return PipelineError(stage=stage, code=code or fallback_code, message=message)

    def _extract_error_code(self, message: str) -> str | None:
        head = message.split(":", 1)[0].strip().upper().replace(" ", "_")
        if head in {
            "UNSUPPORTED_FILE_TYPE",
            "FILE_TOO_LARGE",
            "EMPTY_FILE",
            "UNSUPPORTED_TEXT_ENCODING",
            "PARSE_FAILED",
            "NO_TEXT_EXTRACTED",
            "CHUNK_FAILED",
            "INDEX_FAILED",
        }:
            return head
        return None
