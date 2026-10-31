"""Convert Sarvam Extract output into the application's common policy shape.

The normaliser is intentionally conservative:

* absent or placeholder values stay ``None``;
* a clearly non-insurance document is never added as a policy;
* uncertain or incomplete insurance results are added to a Needs review queue;
* OCR status is never presented as insurer verification or active cover.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from src.insurance_inventory import (
    derive_display_status,
    display_value,
    mask_policy_number,
    normalise_date,
)
from src.mock_paytm_data import timestamp_now

PRODUCT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("health", ("health", "mediclaim", "hospital", "aarogya", "critical illness")),
    ("life", ("life", "term plan", "term insurance", "endowment", "ulip", "jeevan")),
    ("motor", ("motor", "vehicle", "car ", "bike", "two-wheeler", "auto cover")),
    ("travel", ("travel", "trip", "flight", "yatra")),
)

INSURANCE_TERMS = (
    "insurance",
    "policy",
    "policy schedule",
    "sum insured",
    "premium",
    "insurer",
    "uin",
    "renewal",
)
NON_INSURANCE_TERMS = (
    "invoice",
    "receipt",
    "bank statement",
    "account statement",
    "aadhaar",
    "pan card",
    "driving licence",
    "driving license",
    "vehicle registration",
    "rc book",
    "salary slip",
    "payslip",
    "tax return",
    "passport",
    "boarding pass",
    "ticket",
    "prescription",
    "discharge summary",
    "lab report",
    "identity card",
    "utility bill",
)

PLACEHOLDER_VALUES = {
    "not found",
    "not found in document",
    "n/a",
    "na",
    "none",
    "null",
    "-",
    "—",
}
DocumentDecision = Literal["insurance", "not_insurance", "uncertain"]
RecordDecision = Literal["added", "not_policy"]

REVIEW_UPDATE_FIELDS = (
    "insurer_name",
    "product_name",
    "product_type",
    "policy_number_full",
    "uin",
    "policy_start_date",
    "policy_end_date",
    "sum_insured",
    "premium_amount",
    "premium_frequency",
    "policyholder_name",
    "insured_persons",
    "ocr_nominee_name",
    "ocr_nominee_relationship",
)


@dataclass(frozen=True)
class ExternalPolicyResult:
    decision: RecordDecision
    record: dict[str, Any] | None
    message: str
    review_reasons: tuple[str, ...] = ()
    document_type: str | None = None

    @property
    def added(self) -> bool:
        return self.record is not None and self.decision == "added"

    @property
    def needs_review(self) -> bool:
        return bool(self.record) and bool(self.review_reasons)


def _clean(value: object) -> str | None:
    """Return a stripped scalar or ``None``; never fabricate a value."""
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    text = str(value).strip()
    if not text or text.lower() in PLACEHOLDER_VALUES:
        return None
    return text


def _combined_text(extracted: Mapping[str, Any]) -> str:
    parts = [
        _clean(extracted.get(key)) or ""
        for key in (
            "document_type",
            "insurer_name",
            "product_name",
            "policy_number",
            "uin",
        )
    ]
    return " ".join(part for part in parts if part).lower()


def normalise_product_type(extracted: Mapping[str, Any]) -> str:
    text = _combined_text(extracted)
    for product_type, keywords in PRODUCT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return product_type
    return "unknown"


def classify_document(extracted: Mapping[str, Any]) -> DocumentDecision:
    """Classify only from extracted text; uncertainty is not discarded."""
    document_type = (_clean(extracted.get("document_type")) or "").lower()
    insurer = _clean(extracted.get("insurer_name"))
    product_type = normalise_product_type(extracted)
    combined = _combined_text(extracted)

    # An explicit non-insurance document type wins even if the page contains
    # insurance words (for example an insurance-premium receipt or a bank
    # statement that mentions a policy). Such a document is not a policy record.
    if any(term in document_type for term in NON_INSURANCE_TERMS):
        return "not_insurance"
    insurance_signal = (
        any(term in document_type for term in INSURANCE_TERMS)
        or any(term in combined for term in ("insurance", "policy schedule"))
        or insurer is not None
        or product_type != "unknown"
    )
    if insurance_signal:
        return "insurance"
    return "uncertain"


def build_external_policy(
    extracted: Mapping[str, Any],
    *,
    document_name: str,
    owner_demo_user_id: str,
    now: datetime | None = None,
) -> ExternalPolicyResult:
    """Create a session-only external policy record after a Sarvam response."""
    decision = classify_document(extracted)
    document_type = _clean(extracted.get("document_type"))
    if decision == "not_insurance":
        return ExternalPolicyResult(
            decision="not_policy",
            record=None,
            message=(
                "This document was not identified as an insurance policy. "
                "No policy was added."
            ),
            document_type=document_type,
        )

    insurer_name = _clean(extracted.get("insurer_name"))
    product_name = _clean(extracted.get("product_name"))
    product_type = normalise_product_type(extracted)
    raw_policy_number = _clean(extracted.get("policy_number"))
    insured_text = _clean(extracted.get("insured_persons"))
    start_date = normalise_date(extracted.get("policy_start_date"))
    end_date = normalise_date(extracted.get("policy_end_date"))

    review_reasons: list[str] = []
    if decision == "uncertain":
        review_reasons.append(
            "Document type was not confidently identified as an insurance policy."
        )
    if insurer_name is None:
        review_reasons.append("Insurer name was not found in the document.")
    if raw_policy_number is None:
        review_reasons.append("Policy number was not found in the document.")
    if start_date is None and end_date is None:
        review_reasons.append("Policy dates were not found in the document.")

    safe_name = Path(str(document_name or "")).name.strip()[:200]
    record: dict[str, Any] = {
        "policy_id": f"external-{uuid4().hex}",
        "source_type": "EXTERNAL_DOCUMENT",
        "owner_demo_user_id": owner_demo_user_id,
        "insurer_name": insurer_name,
        "product_name": product_name,
        "product_type": product_type,
        "policy_number_masked": mask_policy_number(raw_policy_number),
        "policy_number_full": raw_policy_number,
        "uin": _clean(extracted.get("uin")),
        "policy_start_date": start_date,
        "policy_end_date": end_date,
        "sum_insured": _clean(extracted.get("sum_insured")),
        "premium_amount": _clean(extracted.get("premium_amount")),
        "premium_frequency": _clean(extracted.get("premium_frequency")),
        "policyholder_name": _clean(extracted.get("policyholder_name")),
        "insured_persons": [insured_text] if insured_text else [],
        "ocr_nominee_name": _clean(extracted.get("nominee_name")),
        "ocr_nominee_relationship": _clean(
            extracted.get("nominee_relationship")
        ),
        "verification_status": "OCR_EXTRACTED_NEEDS_REVIEW",
        "created_at": (
            now or datetime.now().astimezone()
        ).isoformat(timespec="seconds"),
        "document_name": safe_name or "Uploaded document",
        "document_type": document_type,
        "raw_extracted": copy.deepcopy(dict(extracted)),
        "review_reasons": review_reasons,
    }
    record["display_status"] = derive_display_status(record)
    return ExternalPolicyResult(
        decision="added",
        record=record,
        message=(
            "External policy record created with status "
            "OCR_EXTRACTED_NEEDS_REVIEW. Review the extracted fields before "
            "using this record."
        ),
        review_reasons=tuple(review_reasons),
        document_type=document_type,
    )


def _review_date(value: object, label: str) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    normalised = normalise_date(text)
    if normalised is None:
        raise ValueError(f"{label} must be a valid date (for example 2026-04-01).")
    return normalised


def review_external_policy(
    record: Mapping[str, Any],
    updates: Mapping[str, Any],
    *,
    authorised: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply user corrections and mark the record USER_REVIEWED_UNVERIFIED."""
    if authorised is not True:
        raise ValueError(
            "Confirm that the document is yours or that you are authorised to add "
            "it before saving the review."
        )
    if record.get("source_type") != "EXTERNAL_DOCUMENT":
        raise ValueError("Only external document records can be reviewed here.")

    updated = copy.deepcopy(dict(record))
    for key in REVIEW_UPDATE_FIELDS:
        if key not in updates:
            continue
        value = updates[key]
        if key == "insured_persons":
            if isinstance(value, (list, tuple)):
                updated[key] = [
                    str(item).strip()
                    for item in value
                    if str(item).strip()
                ]
            else:
                cleaned = _clean(value)
                updated[key] = [cleaned] if cleaned else []
        elif key == "policy_start_date":
            updated[key] = _review_date(value, "Policy start date")
        elif key == "policy_end_date":
            updated[key] = _review_date(value, "Policy end date")
        elif key == "product_type":
            product_type = _clean(value) or "unknown"
            if product_type not in {
                "health",
                "life",
                "motor",
                "travel",
                "other",
                "unknown",
            }:
                raise ValueError("Choose a supported product type.")
            updated[key] = product_type
        elif key == "policy_number_full":
            cleaned = _clean(value)
            updated[key] = cleaned
            updated["policy_number_masked"] = mask_policy_number(cleaned)
        else:
            updated[key] = _clean(value)

    updated["verification_status"] = "USER_REVIEWED_UNVERIFIED"
    updated["review_reasons"] = []
    updated["reviewed_at"] = (
        now or datetime.now().astimezone()
    ).isoformat(timespec="seconds")
    updated["display_status"] = derive_display_status(updated)
    return updated


def external_record_is_reviewable(record: Mapping[str, Any]) -> bool:
    return (
        record.get("source_type") == "EXTERNAL_DOCUMENT"
        and record.get("verification_status") == "OCR_EXTRACTED_NEEDS_REVIEW"
    )


def policy_field(record: Mapping[str, Any], key: str) -> str:
    return display_value(record.get(key))


__all__ = [
    "ExternalPolicyResult",
    "build_external_policy",
    "classify_document",
    "external_record_is_reviewable",
    "normalise_product_type",
    "policy_field",
    "review_external_policy",
]
