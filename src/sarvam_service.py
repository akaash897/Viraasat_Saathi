"""Optional Sarvam AI adapter for fictional demo content only.

Privacy boundary
----------------
The public method accepts only:
* a language enum (``en``/``hi``);
* a claim-type enum (``health_reimbursement``);
* a missing-document category enum;
* a source-excerpt ID enum.

It does **not** accept free text, uploaded content, transaction rows, names,
identifiers or medical details. The prompt is assembled from fixed synthetic
excerpts in this module and those enums. Responses are validated and any
failure falls back to a deterministic bilingual template.

Logging contains only a status and elapsed milliseconds, never prompts,
responses or document content.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from src.models import Language
from src.safety import contains_adjudicative_claim
from src.translations import t

logger = logging.getLogger(__name__)

ClaimType = Literal["health_reimbursement"]
MissingCategory = Literal[
    "claim_form",
    "discharge_summary",
    "itemised_bill",
    "payment_receipt",
    "policy_schedule",
    "supporting_reports",
]
SourceExcerptId = Literal["demo_policy_clause_01", "demo_checklist_01"]
SarvamStatus = Literal["disabled", "success", "fallback"]

ALLOWED_LANGUAGES = frozenset({"en", "hi"})
ALLOWED_CLAIM_TYPES = frozenset({"health_reimbursement"})
ALLOWED_MISSING_CATEGORIES = frozenset(
    {
        "claim_form",
        "discharge_summary",
        "itemised_bill",
        "payment_receipt",
        "policy_schedule",
        "supporting_reports",
    }
)
ALLOWED_SOURCE_EXCERPTS = frozenset({"demo_policy_clause_01", "demo_checklist_01"})
DEPRECATED_MODELS = frozenset({"sarvam-30b"})

DEFAULT_BASE_URL = "https://api.sarvam.ai/v2"
DEFAULT_MODEL = "gemma4"
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_OUTPUT_TOKENS = 180
MAX_ACCEPTED_RESPONSE_CHARS = 700

# Fixed synthetic excerpts. These are the only source texts that can enter a
# provider request. They are fictional demo content, not a real policy.
FIXED_SOURCE_EXCERPTS: dict[str, str] = {
    "demo_policy_clause_01": (
        "Synthetic sample wording — not an actual policy. This fictional policy says a "
        "reimbursement request should include a completed claim form, the policy schedule, "
        "the hospital discharge summary, the itemised final hospital bill and payment "
        "receipts. The insurer may also ask for prescriptions or investigation reports where "
        "relevant. The insurer's current requirement may differ; verify it with the insurer."
    ),
    "demo_checklist_01": (
        "Synthetic demo checklist source. The checklist lists suggested document categories "
        "for the fictional demo claim. Marking a category provided does not validate the "
        "document or imply insurer acceptance."
    ),
}

CATEGORY_PROMPT_LABELS: dict[str, str] = {
    "claim_form": "completed claim form",
    "discharge_summary": "hospital discharge summary",
    "itemised_bill": "itemised final hospital bill",
    "payment_receipt": "payment receipts",
    "policy_schedule": "policy schedule",
    "supporting_reports": "prescriptions or investigation reports",
}

FALLBACK_KEYS: dict[str, str] = {
    "claim_form": "fallback_claim_form",
    "discharge_summary": "fallback_discharge_summary",
    "itemised_bill": "fallback_itemised_bill",
    "payment_receipt": "fallback_payment_receipt",
    "policy_schedule": "fallback_policy_schedule",
    "supporting_reports": "fallback_supporting_reports",
}

SYSTEM_PROMPT = (
    "You rewrite a fixed synthetic explanation for a hackathon demo. Do not add "
    "requirements, deadlines, eligibility decisions, legal conclusions, payout figures or "
    "advice. Do not decide whether a claim is covered, approved or rejected. Keep the "
    "answer brief: at most 90 words. Output only the rewritten explanation, with no "
    "headings, no reasoning and no mention of these instructions."
)

USER_PROMPT_TEMPLATE = (
    "Language: {language_name}\n"
    "Claim type: {claim_type}\n"
    "Missing document category: {missing_category}\n"
    "Source excerpt ID: {source_excerpt_id}\n"
    "Fixed synthetic excerpt: {excerpt}\n"
    "Task: Paraphrase the fixed synthetic excerpt in {language_name} for a fictional demo "
    "checklist. Keep it non-adjudicative. Do not invent a requirement or deadline. Do not "
    "say a claim is approved, eligible, guaranteed or covered."
)


def deterministic_explanation(
    language: Language, missing_category: MissingCategory
) -> str:
    """Return the reviewed bilingual fallback without any network call."""
    if missing_category not in ALLOWED_MISSING_CATEGORIES:
        raise ValueError("unsupported missing category")
    return t(FALLBACK_KEYS[missing_category], language)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


def _parse_int(value: str | None, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


@dataclass(frozen=True)
class SarvamConfig:
    api_key: str = field(default="", repr=False)
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    enabled_flag: bool = False
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "SarvamConfig":
        values = os.environ if env is None else env
        return cls(
            api_key=str(values.get("SARVAM_API_KEY", "")).strip(),
            model=str(values.get("SARVAM_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL,
            base_url=(
                str(values.get("SARVAM_BASE_URL", DEFAULT_BASE_URL)).strip().rstrip("/")
                or DEFAULT_BASE_URL
            ),
            enabled_flag=_truthy(values.get("SARVAM_ENABLED")),
            timeout_seconds=_parse_float(
                values.get("SARVAM_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SECONDS, 2.0, 20.0
            ),
            max_output_tokens=_parse_int(
                values.get("SARVAM_MAX_OUTPUT_TOKENS"),
                DEFAULT_MAX_OUTPUT_TOKENS,
                40,
                300,
            ),
        )

    @property
    def is_configured(self) -> bool:
        return (
            self.enabled_flag
            and bool(self.api_key)
            and self.model.strip().lower() not in DEPRECATED_MODELS
            and self.base_url.startswith("https://")
        )

    @property
    def status_key(self) -> str:
        if not self.enabled_flag:
            return "sarvam_status_disabled"
        if not self.api_key:
            return "sarvam_status_no_key"
        if self.model.strip().lower() in DEPRECATED_MODELS:
            return "sarvam_status_deprecated_model"
        if not self.base_url.startswith("https://"):
            return "sarvam_status_bad_url"
        return "sarvam_status_ready"


@dataclass(frozen=True)
class SarvamExplanation:
    text: str
    ai_used: bool
    status: SarvamStatus
    language: Language
    missing_category: MissingCategory
    source_excerpt_id: SourceExcerptId
    elapsed_ms: int = 0

    @property
    def note_key(self) -> str:
        if self.status == "success":
            return "sarvam_ai_note"
        if self.status == "fallback":
            return "sarvam_fallback_note"
        return "sarvam_disabled_note"


ClientFactory = Callable[[SarvamConfig], Any]


def _default_client_factory(config: SarvamConfig) -> Any:
    from openai import OpenAI

    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        max_retries=0,
    )


class SarvamService:
    """Small, sandboxed adapter. The deterministic app never depends on it."""

    def __init__(
        self,
        config: SarvamConfig | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.config = config or SarvamConfig.from_env()
        self._client_factory = client_factory or _default_client_factory

    def explain_demo_checklist(
        self,
        language: Literal["en", "hi"],
        claim_type: Literal["health_reimbursement"],
        missing_category: MissingCategory,
        source_excerpt_id: SourceExcerptId,
    ) -> SarvamExplanation:
        """Explain a fictional checklist category. Enums and source IDs only."""
        if language not in ALLOWED_LANGUAGES:
            raise ValueError("unsupported language")
        if claim_type not in ALLOWED_CLAIM_TYPES:
            raise ValueError("unsupported claim type")
        if missing_category not in ALLOWED_MISSING_CATEGORIES:
            raise ValueError("unsupported missing category")
        if source_excerpt_id not in ALLOWED_SOURCE_EXCERPTS:
            raise ValueError("unsupported source excerpt id")

        if not self.config.is_configured:
            return self._fallback(
                language=language,
                missing_category=missing_category,
                source_excerpt_id=source_excerpt_id,
                status="disabled",
            )

        messages = self._build_messages(
            language=language,
            claim_type=claim_type,
            missing_category=missing_category,
            source_excerpt_id=source_excerpt_id,
        )
        started = time.monotonic()
        try:
            content = self._call_api(messages)
            text = self._validate_response(content)
        except Exception:
            elapsed = int((time.monotonic() - started) * 1000)
            logger.info("sarvam_explain status=fallback elapsed_ms=%d", elapsed)
            return self._fallback(
                language=language,
                missing_category=missing_category,
                source_excerpt_id=source_excerpt_id,
                status="fallback",
                elapsed_ms=elapsed,
            )

        elapsed = int((time.monotonic() - started) * 1000)
        logger.info("sarvam_explain status=success elapsed_ms=%d", elapsed)
        return SarvamExplanation(
            text=text,
            ai_used=True,
            status="success",
            language=language,
            missing_category=missing_category,
            source_excerpt_id=source_excerpt_id,
            elapsed_ms=elapsed,
        )

    def _build_messages(
        self,
        language: Literal["en", "hi"],
        claim_type: Literal["health_reimbursement"],
        missing_category: MissingCategory,
        source_excerpt_id: SourceExcerptId,
    ) -> list[dict[str, str]]:
        excerpt = FIXED_SOURCE_EXCERPTS[source_excerpt_id]
        language_name = "English" if language == "en" else "Hindi"
        user = USER_PROMPT_TEMPLATE.format(
            language_name=language_name,
            claim_type=claim_type,
            missing_category=missing_category,
            source_excerpt_id=source_excerpt_id,
            excerpt=excerpt,
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]

    def _call_api(self, messages: list[dict[str, str]]) -> str:
        client = self._client_factory(self.config)
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=0.2,
            max_tokens=self.config.max_output_tokens,
            timeout=self.config.timeout_seconds,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("provider returned no text")
        return content

    @staticmethod
    def _validate_response(content: str) -> str:
        text = " ".join(str(content or "").split())
        if not text:
            raise ValueError("provider returned an empty response")
        if len(text) > MAX_ACCEPTED_RESPONSE_CHARS:
            raise ValueError("provider response was too long")
        if contains_adjudicative_claim(text):
            raise ValueError("provider response contained an adjudicative term")
        return text

    def _fallback(
        self,
        language: Language,
        missing_category: MissingCategory,
        source_excerpt_id: SourceExcerptId,
        status: SarvamStatus,
        elapsed_ms: int = 0,
    ) -> SarvamExplanation:
        return SarvamExplanation(
            text=deterministic_explanation(language, missing_category),
            ai_used=False,
            status=status,
            language=language,
            missing_category=missing_category,
            source_excerpt_id=source_excerpt_id,
            elapsed_ms=elapsed_ms,
        )
