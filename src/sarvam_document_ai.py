"""Real Sarvam Document AI Extract adapter.

The adapter uses the current ``sarvamai`` SDK: submit ``client.doc_ai.extract``,
poll ``get_status`` to a terminal state, then read ``get_results``. It never
returns fabricated OCR data. When the key is absent or the job fails, it raises
a safe, user-facing error and the caller keeps the seeded demo inventory.

Privacy: uploads are passed as an in-memory buffer, results are returned to the
caller for session-only storage, and logging never includes file contents,
extracted values, policy numbers, names or API keys.
"""

from __future__ import annotations

import inspect
import io
import logging
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.policy_extraction_schema import extraction_schema_json

logger = logging.getLogger(__name__)

DEFAULT_DOCUMENT_LANGUAGE = "en-IN"
ALLOWED_DOCUMENT_LANGUAGES = ("en-IN", "hi-IN", "bn-IN")
DEFAULT_JOB_TIMEOUT_SECONDS = 120.0
DEFAULT_POLL_INTERVAL_SECONDS = 3.0
RESULT_STATUSES = frozenset({"completed", "partially_completed"})
ERROR_STATUSES = frozenset({"failed", "rejected"})
PLACEHOLDER_MARKERS = (
    "replace",
    "placeholder",
    "your_",
    "your-",
    "changeme",
    "change_me",
    "paste_",
    "xxxx",
)


class DocumentAiError(RuntimeError):
    """Safe, user-facing error with no document content or secret material."""


class DocumentAiNotConfigured(DocumentAiError):
    """Live document extraction is disabled or the key is missing."""


class DocumentAiTimeout(DocumentAiError):
    """The asynchronous job exceeded the application's overall timeout."""


class DocumentAiJobFailed(DocumentAiError):
    """Sarvam returned ``failed`` or ``rejected``."""


class DocumentAiResponseError(DocumentAiError):
    """Sarvam returned a response the adapter could not interpret safely."""


@dataclass(frozen=True)
class DocumentAiConfig:
    api_key: str = field(default="", repr=False)
    enabled_flag: bool = False
    language: str = DEFAULT_DOCUMENT_LANGUAGE
    job_timeout_seconds: float = DEFAULT_JOB_TIMEOUT_SECONDS
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DocumentAiConfig":
        values = os.environ if env is None else env
        language = (
            str(values.get("SARVAM_DOCUMENT_LANGUAGE", DEFAULT_DOCUMENT_LANGUAGE))
            .strip()
        )
        if language not in ALLOWED_DOCUMENT_LANGUAGES:
            language = DEFAULT_DOCUMENT_LANGUAGE
        return cls(
            api_key=str(values.get("SARVAM_API_KEY", "")).strip(),
            enabled_flag=_truthy(values.get("SARVAM_ENABLED")),
            language=language,
            job_timeout_seconds=_parse_float(
                values.get("SARVAM_JOB_TIMEOUT_SECONDS"),
                DEFAULT_JOB_TIMEOUT_SECONDS,
                1.0,
                600.0,
            ),
            poll_interval_seconds=_parse_float(
                values.get("SARVAM_POLL_INTERVAL_SECONDS"),
                DEFAULT_POLL_INTERVAL_SECONDS,
                0.1,
                30.0,
            ),
        )

    @property
    def has_api_key(self) -> bool:
        lowered = self.api_key.strip().lower()
        return bool(lowered) and not any(
            marker in lowered for marker in PLACEHOLDER_MARKERS
        )

    @property
    def is_configured(self) -> bool:
        return self.enabled_flag and self.has_api_key

    @property
    def disabled_message(self) -> str:
        if not self.enabled_flag:
            return (
                "Sarvam Document AI is disabled. Set SARVAM_ENABLED=true and add "
                "SARVAM_API_KEY to .env to enable document extraction."
            )
        if not self.has_api_key:
            return "Add SARVAM_API_KEY to .env to enable document extraction."
        return "Sarvam Document AI is configured for live document extraction."


@dataclass(frozen=True)
class ExtractionOutcome:
    job_id: str
    status: str
    result: dict[str, Any]
    partial: bool
    elapsed_ms: int


ProgressCallback = Callable[[str, str], None]
ClientFactory = Callable[[DocumentAiConfig], Any]


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(
    value: str | None, default: float, low: float, high: float
) -> float:
    try:
        parsed = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


def _default_client_factory(config: DocumentAiConfig) -> Any:
    try:
        from sarvamai import SarvamAI
    except ImportError as exc:
        raise DocumentAiError(
            "The Sarvam SDK is not installed. Run pip install -U sarvamai and retry."
        ) from exc
    return SarvamAI(
        api_subscription_key=config.api_key,
        timeout=min(30.0, config.job_timeout_seconds),
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dict(dumped)
    legacy_dict = getattr(value, "dict", None)
    if callable(legacy_dict):
        dumped = legacy_dict()
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise DocumentAiResponseError(
        "Sarvam Document AI returned an unreadable response. No policy was added."
    )


def _response_field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _status_of(value: Any) -> str:
    status = _response_field(value, "status")
    if status is None:
        raise DocumentAiResponseError(
            "Sarvam Document AI did not return a job status. No policy was added."
        )
    return str(status).strip().lower()


class SarvamDocumentAI:
    """Thin, testable adapter around the current Sarvam Document AI SDK."""

    def __init__(
        self,
        config: DocumentAiConfig | None = None,
        *,
        client_factory: ClientFactory | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config or DocumentAiConfig.from_env()
        self._client_factory = client_factory or _default_client_factory
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep

    def extract_policy(
        self,
        raw: bytes,
        *,
        filename: str,
        mime_type: str,
        language: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> ExtractionOutcome:
        """Submit, poll and retrieve an Extract job. No fallback OCR data."""
        if not self.config.is_configured:
            raise DocumentAiNotConfigured(self.config.disabled_message)
        if not raw:
            raise DocumentAiError("The selected file is empty. No policy was added.")

        selected_language = language or self.config.language
        if selected_language not in ALLOWED_DOCUMENT_LANGUAGES:
            selected_language = self.config.language

        started = self._clock()
        client: Any | None = None
        doc_ai: Any | None = None
        try:
            client = self._client_factory(self.config)
            doc_ai = client.doc_ai
            _emit(progress, "submitting", "Submitting the document to Sarvam Document AI…")
            job = self._submit_extract(
                doc_ai,
                raw=raw,
                filename=filename,
                mime_type=mime_type,
                language=selected_language,
            )
            job_id = _response_field(job, "job_id")
            if not job_id:
                raise DocumentAiResponseError(
                    "Sarvam Document AI did not return a job id. No policy was added."
                )
            job_id = str(job_id)
            _emit(progress, "submitted", f"Extraction job accepted ({job_id}).")

            status = self._poll_job(doc_ai, job_id=job_id, progress=progress)
            if status == "failed":
                raise DocumentAiJobFailed(
                    "Sarvam Document AI could not complete extraction "
                    "(status: failed). No policy was added."
                )
            if status == "rejected":
                raise DocumentAiJobFailed(
                    "Sarvam Document AI rejected this document "
                    "(status: rejected). No policy was added."
                )

            _emit(progress, "results", "Retrieving structured extraction results…")
            result = self._fetch_results(doc_ai, job_id=job_id)
            partial = status == "partially_completed"
            elapsed_ms = int((self._clock() - started) * 1000)
            _emit(
                progress,
                status,
                (
                    "Sarvam returned partially completed results; missing fields "
                    "remain Not found in document."
                    if partial
                    else "Sarvam extraction completed. Review all fields."
                ),
            )
            logger.info(
                "sarvam_doc_ai status=%s partial=%s elapsed_ms=%d",
                status,
                partial,
                elapsed_ms,
            )
            return ExtractionOutcome(
                job_id=job_id,
                status=status,
                result=result,
                partial=partial,
                elapsed_ms=elapsed_ms,
            )
        except DocumentAiError as exc:
            logger.warning(
                "sarvam_doc_ai status=error error_type=%s", type(exc).__name__
            )
            raise
        except Exception as exc:  # SDK/network errors: never log contents
            logger.warning(
                "sarvam_doc_ai status=error error_type=%s", type(exc).__name__
            )
            raise DocumentAiError(
                "Sarvam Document AI could not process this document. No policy "
                "was added. Check the API key, network connection and document, "
                "then try again."
            ) from exc
        finally:
            # Release the in-memory upload buffer as soon as the request ends.
            client = None
            doc_ai = None

    def _submit_extract(
        self,
        doc_ai: Any,
        *,
        raw: bytes,
        filename: str,
        mime_type: str,
        language: str,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "file": [
                (
                    Path(str(filename or "document")).name,
                    io.BytesIO(raw),
                    mime_type,
                )
            ],
            "schema": extraction_schema_json(),
            "output_format": "json",
        }
        try:
            parameters = inspect.signature(doc_ai.extract).parameters
        except (TypeError, ValueError):
            parameters = {}
        if "language" in parameters:
            kwargs["language"] = language
        else:
            # Some current SDK builds expose the documented multipart
            # ``language`` field only through request options. The API accepts
            # it as a form field, so pass it without using an undocumented
            # response assumption.
            kwargs["request_options"] = {
                "additional_body_parameters": {"language": language}
            }
        return doc_ai.extract(**kwargs)

    def _poll_job(
        self,
        doc_ai: Any,
        *,
        job_id: str,
        progress: ProgressCallback | None,
    ) -> str:
        deadline = self._clock() + self.config.job_timeout_seconds
        while True:
            response = doc_ai.get_status(job_id=job_id)
            status = _status_of(response)
            _emit(progress, "polling", f"Sarvam job status: {status}.")
            if status in RESULT_STATUSES:
                return status
            if status in ERROR_STATUSES:
                return status

            remaining = deadline - self._clock()
            if remaining <= 0:
                raise DocumentAiTimeout(
                    "Sarvam Document AI did not finish within "
                    f"{int(self.config.job_timeout_seconds)} seconds. No policy "
                    "was added. Try again, or upload a smaller document."
                )
            self._sleep(min(self.config.poll_interval_seconds, remaining))

    def _fetch_results(self, doc_ai: Any, *, job_id: str) -> dict[str, Any]:
        response = doc_ai.get_results(job_id=job_id)
        payload = _as_mapping(response)
        response_type = payload.get("type")
        if response_type not in (None, "extract"):
            raise DocumentAiResponseError(
                "Sarvam returned results for a different document operation. "
                "No policy was added."
            )
        result = payload.get("result")
        if not isinstance(result, Mapping):
            try:
                result = _as_mapping(result)
            except DocumentAiResponseError as exc:
                raise DocumentAiResponseError(
                    "Sarvam did not return structured extraction values. "
                    "No policy was added."
                ) from exc
        return dict(result)


def _emit(
    progress: ProgressCallback | None, stage: str, message: str
) -> None:
    if progress is None:
        return
    try:
        progress(stage, message)
    except Exception:
        # A UI progress callback must never break the extraction flow.
        return


__all__ = [
    "ALLOWED_DOCUMENT_LANGUAGES",
    "DEFAULT_DOCUMENT_LANGUAGE",
    "DocumentAiConfig",
    "DocumentAiError",
    "DocumentAiJobFailed",
    "DocumentAiNotConfigured",
    "DocumentAiResponseError",
    "DocumentAiTimeout",
    "ExtractionOutcome",
    "SarvamDocumentAI",
]
