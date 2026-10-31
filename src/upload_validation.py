"""Application-level validation for external insurance uploads.

The hackathon limits are intentionally smaller than the provider's limits:
10 MB and 20 PDF pages, with PDF, PNG, JPG and JPEG only. Validation happens
entirely in memory and never writes the file to disk or logs its contents.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 20
ALLOWED_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg"})

MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


class UploadValidationError(ValueError):
    """A safe, user-facing upload error that never includes file contents."""


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    page_count: int


def _extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].strip().lower()


def _sniff_matches(extension: str, raw: bytes) -> bool:
    if extension == "pdf":
        return raw.startswith(b"%PDF-")
    if extension == "png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {"jpg", "jpeg"}:
        return raw.startswith(b"\xff\xd8\xff")
    return False


def _pdf_page_count(raw: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise UploadValidationError(
            "PDF support is not installed. Install the project requirements and retry."
        ) from exc
    try:
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise UploadValidationError(
                "This PDF is encrypted. Remove the password and try again."
            )
        return len(reader.pages)
    except UploadValidationError:
        raise
    except Exception as exc:
        raise UploadValidationError(
            "This PDF could not be read. It may be damaged or unsupported."
        ) from exc


def validate_insurance_upload(filename: str, raw: bytes) -> ValidatedUpload:
    """Validate type, magic bytes, size and PDF page count."""
    safe_name = Path(str(filename or "")).name.strip()[:200]
    extension = _extension(safe_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            "Unsupported file type. Upload a PDF, PNG, JPG or JPEG. "
            "ZIP and TIFF are not supported in this phase."
        )
    if not raw:
        raise UploadValidationError("The selected file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadValidationError(
            "The selected file is larger than the 10 MB application limit."
        )
    if not _sniff_matches(extension, raw):
        raise UploadValidationError(
            "The file content does not match its extension. Choose a valid "
            "PDF, PNG, JPG or JPEG."
        )

    page_count = 1
    if extension == "pdf":
        page_count = _pdf_page_count(raw)
        if page_count < 1:
            raise UploadValidationError("The PDF contains no readable pages.")
        if page_count > MAX_PDF_PAGES:
            raise UploadValidationError(
                "The PDF has more than 20 pages. Split it and upload a smaller "
                "document for this prototype."
            )

    return ValidatedUpload(
        filename=safe_name or f"uploaded.{extension}",
        extension=extension,
        mime_type=MIME_TYPES[extension],
        size_bytes=len(raw),
        page_count=page_count,
    )


__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_PDF_PAGES",
    "MAX_UPLOAD_BYTES",
    "UploadValidationError",
    "ValidatedUpload",
    "validate_insurance_upload",
]
