"""Deterministic, editable claim-response drafts.

Drafts use only fictional demo fields and checklist category names. They are
never sent anywhere by the app. No date, legal deadline, coverage conclusion or
payout figure is generated.
"""

from __future__ import annotations

from src.models import DemoClaim, DemoPolicy, DraftKind, Language
from src.translations import t

DRAFT_KIND_KEYS: dict[DraftKind, str] = {
    "missing_document_followup": "draft_missing",
    "claim_status": "draft_status",
    "additional_information": "draft_additional",
    "grievance_preparation": "draft_grievance",
}

DRAFT_KIND_LABEL_KEYS: dict[DraftKind, str] = {
    "missing_document_followup": "draft_kind_missing",
    "claim_status": "draft_kind_status",
    "additional_information": "draft_kind_additional",
    "grievance_preparation": "draft_kind_grievance",
}


def draft_kind_label(kind: DraftKind, language: Language = "en") -> str:
    return t(DRAFT_KIND_LABEL_KEYS[kind], language)


def _none_marked(language: Language) -> str:
    return "None marked yet" if language == "en" else "अभी कोई चिह्नित नहीं"


def _all_marked(language: Language) -> str:
    if language == "en":
        return "None — all categories are marked provided (this is not insurer validation)"
    return "कोई नहीं — सभी श्रेणियाँ प्रदान के रूप में चिह्नित हैं (यह बीमाकर्ता सत्यापन नहीं है)"


def generate_draft(
    kind: DraftKind,
    claim: DemoClaim,
    policy: DemoPolicy,
    provided_ids: set[str],
    missing_category_id: str | None = None,
    language: Language = "en",
) -> str:
    """Return a complete draft with a review reminder."""
    if kind not in DRAFT_KIND_KEYS:
        raise ValueError("unknown draft kind")

    categories = claim.required_document_categories
    marked = [
        item.label_hi if language == "hi" else item.label_en
        for item in categories
        if item.id in provided_ids
    ]
    unmarked = [
        item.label_hi if language == "hi" else item.label_en
        for item in categories
        if item.id not in provided_ids
    ]

    category_label = ""
    if missing_category_id:
        selected = claim.category_by_id(missing_category_id)
        if selected is None:
            raise ValueError("unknown checklist category")
        category_label = selected.label_hi if language == "hi" else selected.label_en
    elif kind in {"missing_document_followup", "additional_information"}:
        first_unmarked = next((item for item in categories if item.id not in provided_ids), None)
        if first_unmarked is not None:
            category_label = (
                first_unmarked.label_hi if language == "hi" else first_unmarked.label_en
            )

    marked_text = "; ".join(marked) if marked else _none_marked(language)
    unmarked_text = "; ".join(unmarked) if unmarked else _all_marked(language)
    if not category_label:
        category_label = (
            "Not specified" if language == "en" else "निर्दिष्ट नहीं"
        )

    prefix = DRAFT_KIND_KEYS[kind]
    subject = t(f"{prefix}_subject", language).format(case_id=claim.case_id)
    body = t(f"{prefix}_body", language).format(
        case_id=claim.case_id,
        policy=policy.policy_name,
        insurer=policy.insurer_label,
        marked=marked_text,
        unmarked=unmarked_text,
        category=category_label,
    )
    return f"{subject}\n\n{body}\n\n---\n{t('draft_demo_only', language)}"
