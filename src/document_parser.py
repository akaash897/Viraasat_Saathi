"""Local-only, in-memory parsing helpers.

Privacy rules enforced here:
* files are read from bytes already held in memory;
* nothing is written to disk;
* document contents and transaction rows are never logged;
* uploads are capped at 10 MB and restricted to PDF, TXT and CSV.

The PDF helper is a readability/navigation aid only. It does not verify
authenticity, sufficiency, coverage or claim eligibility. OCR is not supported.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.models import TransactionRow

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({"pdf", "txt", "csv"})
REQUIRED_TRANSACTION_COLUMNS = ("date", "description", "amount", "direction")


class UploadError(ValueError):
    """A safe, user-facing validation error with no document content."""


def _extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].strip().lower()


def validate_upload(
    filename: str,
    raw: bytes,
    allowed_extensions: frozenset[str] = ALLOWED_EXTENSIONS,
) -> str:
    """Validate a local upload without writing it anywhere."""
    extension = _extension(filename)
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions)).upper()
        raise UploadError(f"Unsupported file type. Allowed types: {allowed}.")
    if not raw:
        raise UploadError("The selected file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("The selected file is larger than the 10 MB limit.")
    return extension


def parse_transactions_csv(raw: bytes) -> list[TransactionRow]:
    """Parse a statement CSV in memory using the expected four-column schema."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("The selected file is larger than the 10 MB limit.")
    if not raw:
        raise UploadError("The selected statement is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError("The CSV must be UTF-8 encoded text.") from exc

    try:
        frame = pd.read_csv(
            io.StringIO(text),
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=True,
        )
    except Exception as exc:  # pandas raises several parser-specific errors
        raise UploadError("The CSV could not be read. Check the four-column format.") from exc

    columns = [str(column).strip().lower() for column in frame.columns]
    if sorted(columns) != sorted(REQUIRED_TRANSACTION_COLUMNS):
        raise UploadError(
            "The CSV must contain exactly these columns: date, description, amount, direction."
        )
    frame.columns = columns
    if frame.empty:
        raise UploadError("The CSV contains no transaction rows.")

    rows: list[TransactionRow] = []
    for index, record in frame.iterrows():
        row_number = int(index) + 2  # header is line 1
        raw_date = str(record["date"]).strip()
        raw_description = str(record["description"]).strip()
        raw_amount = str(record["amount"]).strip().replace(",", "")
        raw_direction = str(record["direction"]).strip().lower()

        if not raw_date or not raw_description or not raw_amount or not raw_direction:
            raise UploadError(f"Row {row_number} is missing a required value.")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise UploadError(f"Row {row_number} has an invalid date; use YYYY-MM-DD.") from exc
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation as exc:
            raise UploadError(f"Row {row_number} has an invalid amount.") from exc
        if amount < 0:
            raise UploadError(f"Row {row_number} has a negative amount; use direction instead.")
        if raw_direction not in {"debit", "credit"}:
            raise UploadError(f"Row {row_number} direction must be debit or credit.")

        try:
            rows.append(
                TransactionRow(
                    row_number=row_number,
                    date=parsed_date,
                    description=raw_description,
                    amount=amount,
                    direction=raw_direction,  # type: ignore[arg-type]
                )
            )
        except Exception as exc:
            raise UploadError(f"Row {row_number} could not be validated.") from exc

    return rows


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class PdfExtraction:
    pages: tuple[PdfPage, ...]
    readable: bool
    message: str
    ocr_supported: bool = False


def extract_pdf_text_in_memory(raw: bytes, max_pages: int = 25) -> PdfExtraction:
    """Extract selectable text from a PDF held in memory.

    Scanned/image-only PDFs return a plain message that OCR is not supported.
    The result is a document-navigation aid, not a coverage or eligibility
    conclusion.
    """
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("The selected file is larger than the 10 MB limit.")
    if not raw:
        raise UploadError("The selected PDF is empty.")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise UploadError("PDF support is not installed.") from exc

    try:
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            return PdfExtraction(
                pages=(),
                readable=False,
                message="This PDF is encrypted. The prototype cannot open it.",
            )
        page_count = len(reader.pages)
        pages: list[PdfPage] = []
        for index, page in enumerate(reader.pages[:max_pages], start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            text = re.sub(r"[ \t]+", " ", text).strip()
            if text:
                pages.append(PdfPage(page_number=index, text=text))
    except Exception:
        return PdfExtraction(
            pages=(),
            readable=False,
            message="This PDF could not be read locally. It may be damaged or unsupported.",
        )

    if not pages:
        return PdfExtraction(
            pages=(),
            readable=False,
            message=(
                "No selectable text was found. OCR is not supported in this prototype, "
                "so a scanned or image-only PDF cannot be read here."
            ),
        )

    suffix = ""
    if page_count > max_pages:
        suffix = f" Only the first {max_pages} pages were read."
    return PdfExtraction(
        pages=tuple(pages),
        readable=True,
        message=(
            "Local text extraction only. This is a document-navigation aid; "
            "verify all wording with the insurer." + suffix
        ),
    )


def extract_text_in_memory(raw: bytes, max_chars: int = 20_000) -> str:
    """Decode a small local TXT file without writing or logging it."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("The selected file is larger than the 10 MB limit.")
    if not raw:
        raise UploadError("The selected text file is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError("The text file must be UTF-8 encoded.") from exc
    return text[:max_chars]
