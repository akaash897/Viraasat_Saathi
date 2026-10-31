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

import json
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

# ===== Sarvam-105B schemas for Phase 2 Update =====

NOMINEE_FINDING_EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "portfolio_summary": {"type": "string"},
        "finding_explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "plain_language_explanation": {"type": "string"},
                    "what_to_verify": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["finding_id", "plain_language_explanation", "what_to_verify", "source_ids"],
            },
        },
        "portfolio_note": {"type": "string"},
    },
    "required": ["portfolio_summary", "finding_explanations", "portfolio_note"],
}

CLAIM_ORCHESTRATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "portfolio_summary": {"type": "string"},
        "workflow_explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "plain_language_explanation": {"type": "string"},
                    "what_to_verify": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["workflow_id", "plain_language_explanation", "what_to_verify", "source_ids"],
            },
        },
        "portfolio_note": {"type": "string"},
    },
    "required": ["portfolio_summary", "workflow_explanations", "portfolio_note"],
}

MAX_105B_OUTPUT_CHARS = 3000

NOMINEE_SYSTEM_PROMPT = (
    "You are an assistant for a hackathon demo. Explain nominee consistency findings "
    "in plain language. Do not decide legal eligibility, identity matches, or insurer "
    "registration. Do not say a nominee is valid/invalid or eligible/ineligible. "
    "Only explain what the finding means and what the user should verify with the insurer. "
    "Output MUST conform to the provided JSON schema. No extra text."
)

NOMINEE_USER_PROMPT_TEMPLATE = (
    "Language: {language_name}\n"
    "Portfolio findings (redacted):\n{findings_json}\n\n"
    "Task: For each finding, provide a plain-language explanation and what to verify. "
    "Group similar findings. Keep explanations non-adjudicative. "
    "Output ONLY valid JSON matching the schema."
)

CLAIM_ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are an assistant for a hackathon demo. Explain a family claim orchestration plan "
    "in plain language. Do not decide coverage, eligibility, claim approval, or settlement. "
    "Only explain the rule engine's output and what the user should verify with each insurer. "
    "Output MUST conform to the provided JSON schema. No extra text."
)

CLAIM_ORCHESTRATOR_USER_PROMPT_TEMPLATE = (
    "Language: {language_name}\n"
    "Family claim batch (redacted):\n{batch_json}\n\n"
    "Task: For each child workflow, explain the event relevance, checklist, and next steps. "
    "Do not invent requirements. Only explain the deterministic rule output. "
    "Output ONLY valid JSON matching the schema."
)

DEFAULT_105B_MODEL = "sarvam-105b"
DEFAULT_105B_TIMEOUT_SECONDS = 10.0
DEFAULT_105B_MAX_OUTPUT_TOKENS = 2000

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

    # ===== Sarvam-105B methods for Phase 2 Update =====

    def explain_nominee_findings(
        self,
        language: Literal["en", "hi"],
        findings: list[dict[str, Any]],
        language_name: str,
    ) -> SarvamExplanation:
        """Explain nominee consistency findings via Sarvam-105B with structured output."""
        if language not in ALLOWED_LANGUAGES:
            raise ValueError("unsupported language")

        if not self.config.is_configured:
            return self._fallback_105b(
                language=language,
                status="disabled",
                explanation_type="nominee",
            )

        findings_json = json.dumps(findings, ensure_ascii=False)
        user_prompt = NOMINEE_USER_PROMPT_TEMPLATE.format(
            language_name=language_name,
            findings_json=findings_json,
        )
        messages = [
            {"role": "system", "content": NOMINEE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        started = time.monotonic()
        try:
            content = self._call_api_105b(messages, NOMINEE_FINDING_EXPLANATION_SCHEMA)
            parsed = json.loads(content)
            # Validate required fields
            if not all(k in parsed for k in ("portfolio_summary", "finding_explanations", "portfolio_note")):
                raise ValueError("response missing required fields")
            text = json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            elapsed = int((time.monotonic() - started) * 1000)
            logger.info("sarvam_105b_nominee status=fallback elapsed_ms=%d error=%s", elapsed, str(e)[:100])
            return self._fallback_105b(
                language=language,
                status="fallback",
                explanation_type="nominee",
                elapsed_ms=elapsed,
            )

        elapsed = int((time.monotonic() - started) * 1000)
        logger.info("sarvam_105b_nominee status=success elapsed_ms=%d", elapsed)
        return SarvamExplanation(
            text=text,
            ai_used=True,
            status="success",
            language=language,
            missing_category="nominee_findings",  # repurposed field
            source_excerpt_id="nominee_360",       # repurposed field
            elapsed_ms=elapsed,
        )

    def explain_claim_orchestrator_plan(
        self,
        language: Literal["en", "hi"],
        batch: dict[str, Any],
        workflows: list[dict[str, Any]],
        playbooks: dict[str, Any],
        language_name: str,
    ) -> SarvamExplanation:
        """Explain family claim orchestrator plan via Sarvam-105B with structured output."""
        if language not in ALLOWED_LANGUAGES:
            raise ValueError("unsupported language")

        if not self.config.is_configured:
            return self._fallback_105b(
                language=language,
                status="disabled",
                explanation_type="claim_orchestrator",
            )

        batch_json = json.dumps({
            "batch_id": batch.get("batch_id"),
            "event_type": batch.get("event_type"),
            "event_date": batch.get("event_date"),
            "deceased_demo_user_id": batch.get("deceased_demo_user_id"),
            "child_workflow_count": len(workflows),
        }, ensure_ascii=False)

        workflows_json = json.dumps([{
            "workflow_id": w.get("workflow_id"),
            "policy_id": w.get("policy_id"),
            "event_relevance": w.get("event_relevance"),
            "claimant_capacity": w.get("claimant_capacity"),
            "playbook_id": w.get("playbook_id"),
            "status": w.get("status"),
        } for w in workflows], ensure_ascii=False)

        playbooks_json = json.dumps({
            pid: {
                "playbook_id": pb.get("playbook_id"),
                "product_type": pb.get("product_type"),
                "required_docs": [d.get("category") for d in pb.get("required_documents", [])],
            } for pid, pb in playbooks.items()
        }, ensure_ascii=False)

        user_prompt = CLAIM_ORCHESTRATOR_USER_PROMPT_TEMPLATE.format(
            language_name=language_name,
            batch_json=f"Batch: {batch_json}\nWorkflows: {workflows_json}\nPlaybooks: {playbooks_json}",
        )
        messages = [
            {"role": "system", "content": CLAIM_ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        started = time.monotonic()
        try:
            content = self._call_api_105b(messages, CLAIM_ORCHESTRATOR_SCHEMA)
            parsed = json.loads(content)
            if not all(k in parsed for k in ("portfolio_summary", "workflow_explanations", "portfolio_note")):
                raise ValueError("response missing required fields")
            text = json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            elapsed = int((time.monotonic() - started) * 1000)
            logger.info("sarvam_105b_claim status=fallback elapsed_ms=%d error=%s", elapsed, str(e)[:100])
            return self._fallback_105b(
                language=language,
                status="fallback",
                explanation_type="claim_orchestrator",
                elapsed_ms=elapsed,
            )

        elapsed = int((time.monotonic() - started) * 1000)
        logger.info("sarvam_105b_claim status=success elapsed_ms=%d", elapsed)
        return SarvamExplanation(
            text=text,
            ai_used=True,
            status="success",
            language=language,
            missing_category="claim_orchestrator",
            source_excerpt_id="family_claims",
            elapsed_ms=elapsed,
        )

    def _call_api_105b(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        """Call LLM with structured output. Uses OpenRouter with Nemotron 3 Ultra (free) by default."""
        # Allow model/provider override via env
        model = os.environ.get("LLM_105B_MODEL", "nvidia/nemotron-3-ultra")
        timeout = float(os.environ.get("LLM_105B_TIMEOUT_SECONDS", str(DEFAULT_105B_TIMEOUT_SECONDS)))
        max_tokens = int(os.environ.get("LLM_105B_MAX_OUTPUT_TOKENS", str(DEFAULT_105B_MAX_OUTPUT_TOKENS)))
        base_url = os.environ.get("LLM_105B_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.environ.get("LLM_105B_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))

        if not api_key:
            raise ValueError("LLM_105B_API_KEY or OPENROUTER_API_KEY not configured")

        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
        )

        # Try 1: response_format with json_schema (OpenAI-compatible)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format={"type": "json_schema", "json_schema": {"name": "structured_output", "schema": schema, "strict": True}},
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError("provider returned empty text")
            json.loads(content)
            return content
        except Exception as e:
            logger.info("LLM response_format failed: %s, falling back to prompt-only", str(e)[:200])

        # Try 2: Prompt-only with schema instructions in system message
        schema_instruction = (
            "\n\nYou MUST output ONLY valid JSON matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}\n"
            "No extra text, no markdown, no explanation."
        )
        fallback_messages = messages.copy()
        fallback_messages[0] = {
            "role": "system",
            "content": fallback_messages[0]["content"] + schema_instruction
        }

        response = client.chat.completions.create(
            model=model,
            messages=fallback_messages,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("provider returned empty text")
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
        json.loads(content)  # Validate
        return content

    def _fallback_105b(
        self,
        language: Language,
        status: SarvamStatus,
        explanation_type: Literal["nominee", "claim_orchestrator"],
        elapsed_ms: int = 0,
    ) -> SarvamExplanation:
        if explanation_type == "nominee":
            fallback_text = (
                "AI explanation unavailable. Deterministic fallback:\n"
                "- Each finding shows the policy, source values, and what to verify with the insurer.\n"
                "- Severity: INFO = informational; ATTENTION = data inconsistency; REVIEW_REQUIRED = needs human check.\n"
                "- Actions: 'Reviewed — no change', 'Correct demo data', 'Intentionally different', 'Ask insurer'.\n"
                "- This is a data-consistency check only — not legal eligibility or insurer registration."
            )
        else:
            fallback_text = (
                "AI explanation unavailable. Deterministic fallback:\n"
                "- Each child workflow corresponds to one policy with a deterministic event relevance.\n"
                "- Life policies with matching insured → potential death claim.\n"
                "- Health policies → only outstanding medical expense enquiry if expenses exist.\n"
                "- Motor policies → only if owner-driver PA cover + accident evidence.\n"
                "- Credit-life → enquiry with lender; proceeds may apply to loan balance.\n"
                "- Checklists come from versioned local playbooks. Confirm every item with the insurer.\n"
                "- No insurer status is implied. User must confirm before any workflow is created."
            )
        return SarvamExplanation(
            text=fallback_text,
            ai_used=False,
            status=status,
            language=language,
            missing_category=explanation_type,
            source_excerpt_id="fallback",
            elapsed_ms=elapsed_ms,
        )
