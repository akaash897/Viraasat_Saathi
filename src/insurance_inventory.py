"""Normalised insurance inventory helpers for the Phase 2 prototype.

All functions are pure and operate on session-safe dictionaries. Nothing here
reads or writes disk, calls a network or persists uploaded documents.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, MutableMapping, Sequence
from datetime import date, datetime
from typing import Any, Literal

from src.mock_paytm_data import paytm_policies_as_dicts

NOT_FOUND = "Not found in document"
SOURCE_LABELS: dict[str, str] = {
    "PAYTM_DEMO": "Bought on Paytm — DEMO",
    "EXTERNAL_DOCUMENT": "External document — OCR output",
    "NOMINEE_SHARED": "Nominee-linked limited summary — DEMO",
}
VERIFICATION_LABELS: dict[str, str] = {
    "SIMULATED_NOT_VERIFIED": "Demo record — not verified with insurer",
    "OCR_EXTRACTED_NEEDS_REVIEW": "OCR extracted — needs review",
    "USER_REVIEWED_UNVERIFIED": "User reviewed — insurer status not verified",
}
NOMINEE_LEGAL_WORDING = (
    "This creates a simulated Paytm-ID family link inside the hackathon "
    "prototype. It does not register, change or confirm a legal nominee with "
    "the insurer. To make or change a legally effective nomination, use the "
    "insurer's official process and obtain its acknowledgement."
)
PROTOTYPE_LABEL = (
    "Independent hackathon prototype · Paytm-style demo · "
    "No live Paytm connection"
)
INSURANCE_SESSION_PREFIX = "vs_insurance_"
POLICY_SOURCE_TYPES = frozenset(
    {"PAYTM_DEMO", "EXTERNAL_DOCUMENT", "NOMINEE_SHARED"}
)
VERIFICATION_STATUSES = frozenset(
    {
        "SIMULATED_NOT_VERIFIED",
        "OCR_EXTRACTED_NEEDS_REVIEW",
        "USER_REVIEWED_UNVERIFIED",
    }
)
PRODUCT_TYPES = ("health", "life", "motor", "travel", "other", "unknown")

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


def mask_policy_number(value: object) -> str | None:
    """Return a masked policy number; never expose the full value in a card."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if any(mark in text for mark in ("•", "*", "…")):
        return text
    if len(text) <= 4:
        return "••••"
    return f"•••• {text[-4:]}"


def normalise_date(value: object) -> str | None:
    """Parse a printed date into ISO form without inventing a missing value."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    cleaned = " ".join(text.replace("Sept", "Sep").split())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def display_value(value: object) -> str:
    """Render a missing OCR field explicitly instead of guessing a value."""
    if value is None:
        return NOT_FOUND
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(parts) if parts else NOT_FOUND
    text = str(value).strip()
    if not text:
        return NOT_FOUND
    if text.lower() in {
        "not found",
        "not found in document",
        "n/a",
        "na",
        "none",
        "null",
        "-",
        "—",
    }:
        return NOT_FOUND
    return text


def display_date(value: object) -> str:
    iso = normalise_date(value)
    if iso is None:
        return NOT_FOUND
    return date.fromisoformat(iso).strftime("%d %b %Y")


def derive_display_status(
    record: Mapping[str, Any], *, as_of: date | None = None
) -> str:
    """Derive a cautious hint; never infer that an insurer has it active."""
    source_type = str(record.get("source_type", ""))
    if source_type == "PAYTM_DEMO":
        return "Demo record — not verified with insurer"

    if source_type == "NOMINEE_SHARED":
        return "Limited summary shared by owner; insurer status not checked"

    verification = str(record.get("verification_status", ""))
    if verification == "OCR_EXTRACTED_NEEDS_REVIEW":
        return "OCR extracted — needs review; insurer status not checked"

    start = normalise_date(record.get("policy_start_date"))
    end = normalise_date(record.get("policy_end_date"))
    if start is None and end is None:
        return "Policy dates not found; insurer status not checked"
    today = as_of or date.today()
    start_date = date.fromisoformat(start) if start else None
    end_date = date.fromisoformat(end) if end else None
    if start_date and end_date:
        if start_date <= today <= end_date:
            return "Date window appears current; insurer status not checked"
        return "Date window appears outside today; insurer status not checked"
    return "Date window incomplete; insurer status not checked"


def paytm_record_from_fixture(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a seeded Paytm fixture into the common policy shape."""
    record: dict[str, Any] = {
        "policy_id": str(policy["policy_id"]),
        "source_type": "PAYTM_DEMO",
        "owner_demo_user_id": str(policy["owner_demo_user_id"]),
        "insurer_name": policy.get("insurer_name"),
        "product_name": policy.get("product_name"),
        "product_type": policy.get("product_type", "unknown"),
        "policy_number_masked": policy.get("policy_number_masked"),
        "policy_number_full": policy.get("policy_number_full"),
        "uin": policy.get("uin"),
        "policy_start_date": policy.get("policy_start_date"),
        "policy_end_date": policy.get("policy_end_date"),
        "sum_insured": policy.get("sum_insured"),
        "premium_amount": policy.get("premium_amount"),
        "premium_frequency": policy.get("premium_frequency"),
        "policyholder_name": policy.get("policyholder_name"),
        "insured_persons": list(policy.get("insured_persons") or []),
        "ocr_nominee_name": None,
        "ocr_nominee_relationship": None,
        "verification_status": "SIMULATED_NOT_VERIFIED",
        "created_at": f"{policy.get('policy_start_date', '')}T00:00:00+05:30",
        "document_name": None,
        "raw_extracted": None,
        "review_reasons": [],
    }
    record["display_status"] = derive_display_status(record)
    return record


def seeded_paytm_records() -> list[dict[str, Any]]:
    return [paytm_record_from_fixture(policy) for policy in paytm_policies_as_dicts()]


def paytm_policies_for_user(
    records: Sequence[Mapping[str, Any]], demo_user_id: str
) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in records
        if record.get("source_type") == "PAYTM_DEMO"
        and record.get("owner_demo_user_id") == demo_user_id
    ]


def external_policies_for_user(
    records: Sequence[Mapping[str, Any]], demo_user_id: str
) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in records
        if record.get("source_type") == "EXTERNAL_DOCUMENT"
        and record.get("owner_demo_user_id") == demo_user_id
    ]


def find_policy(
    records: Sequence[Mapping[str, Any]], policy_id: str
) -> dict[str, Any] | None:
    for record in records:
        if record.get("policy_id") == policy_id:
            return dict(record)
    return None


def all_policy_records(
    paytm_records: Sequence[Mapping[str, Any]],
    external_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [dict(record) for record in paytm_records] + [
        dict(record) for record in external_records
    ]


def link_is_active(link: Mapping[str, Any]) -> bool:
    return (
        link.get("demo_link_status") == "ACTIVE"
        and link.get("nominee_acceptance_status") != "DECLINED"
    )


def active_nominee_link_for_policy(
    links: Sequence[Mapping[str, Any]], policy_id: str
) -> dict[str, Any] | None:
    for link in links:
        if link.get("policy_id") != policy_id:
            continue
        if link_is_active(link):
            return dict(link)
    return None


def link_is_visible_to_nominee(link: Mapping[str, Any], nominee_id: str) -> bool:
    return (
        link.get("nominee_demo_user_id") == nominee_id
        and link_is_active(link)
        and link.get("nominee_acceptance_status")
        in {"PENDING", "ACCEPTED"}
    )


def nominee_invitations_for_user(
    links: Sequence[Mapping[str, Any]], nominee_id: str
) -> list[dict[str, Any]]:
    return [
        dict(link)
        for link in links
        if link_is_visible_to_nominee(link, nominee_id)
    ]


def owner_links_for_user(
    links: Sequence[Mapping[str, Any]], owner_id: str
) -> list[dict[str, Any]]:
    owned = [dict(link) for link in links if link.get("owner_demo_user_id") == owner_id]
    return sorted(owned, key=lambda item: str(item.get("created_at", "")), reverse=True)


def nominee_status_label(link: Mapping[str, Any]) -> str:
    acceptance = str(link.get("nominee_acceptance_status", ""))
    demo_status = str(link.get("demo_link_status", ""))
    if acceptance == "DECLINED":
        return "Demo link declined — insurer nomination not verified"
    if demo_status == "REVOKED":
        return "Demo link revoked — insurer nomination not verified"
    if acceptance == "PENDING":
        return "Awaiting demo acceptance — insurer nomination not verified"
    return "Demo link accepted — insurer nomination not verified"


def limited_shared_summary(
    link: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    nominee_id: str,
) -> dict[str, Any] | None:
    """Return only the summary the owner explicitly allowed and the nominee accepted."""
    if not link_is_visible_to_nominee(link, nominee_id):
        return None
    if link.get("nominee_acceptance_status") != "ACCEPTED":
        return None
    if link.get("owner_authorised_summary_sharing") is not True:
        return None
    policy = find_policy(records, str(link.get("policy_id", "")))
    if policy is None:
        return None
    summary = {
        "policy_id": policy.get("policy_id"),
        "source_type": "NOMINEE_SHARED",
        "owner_demo_user_id": policy.get("owner_demo_user_id"),
        "insurer_name": policy.get("insurer_name"),
        "product_name": policy.get("product_name"),
        "product_type": policy.get("product_type"),
        "policy_number_masked": policy.get("policy_number_masked"),
        "policy_start_date": policy.get("policy_start_date"),
        "policy_end_date": policy.get("policy_end_date"),
        "sum_insured": policy.get("sum_insured"),
        "verification_status": policy.get("verification_status"),
        "created_at": policy.get("created_at"),
    }
    summary["display_status"] = derive_display_status(summary)
    return summary


def ensure_insurance_session(
    state: MutableMapping[str, Any],
    users: Sequence[Mapping[str, Any]],
    seed_links: Sequence[Mapping[str, Any]],
) -> None:
    """Initialise Phase 2 session state once, without overwriting user actions."""
    if "vs_insurance_links" not in state:
        state["vs_insurance_links"] = copy.deepcopy(list(seed_links))
    if "vs_insurance_external_policies" not in state:
        state["vs_insurance_external_policies"] = []
    if "vs_insurance_upload_nonce" not in state:
        state["vs_insurance_upload_nonce"] = 0

    user_ids = [str(user.get("demo_user_id")) for user in users]
    active = state.get("vs_insurance_active_user_id")
    if active not in user_ids:
        default = next(
            (
                str(user["demo_user_id"])
                for user in users
                if user.get("is_default")
            ),
            user_ids[0] if user_ids else "",
        )
        state["vs_insurance_active_user_id"] = default
    if state.get("vs_insurance_section") not in {"bought", "external", "nominee"}:
        state["vs_insurance_section"] = "bought"


def reset_insurance_session(
    state: MutableMapping[str, Any],
    users: Sequence[Mapping[str, Any]],
    seed_links: Sequence[Mapping[str, Any]],
) -> None:
    """Remove session-created insurance data and restore the seeded fixtures."""
    for key in list(state.keys()):
        if isinstance(key, str) and key.startswith(INSURANCE_SESSION_PREFIX):
            del state[key]
    state["vs_insurance_links"] = copy.deepcopy(list(seed_links))
    state["vs_insurance_external_policies"] = []
    state["vs_insurance_upload_nonce"] = 0
    state["vs_insurance_section"] = "bought"
    ensure_insurance_session(state, users, seed_links)


def remove_external_policy_session(
    state: MutableMapping[str, Any], policy_id: str
) -> bool:
    external = [
        dict(record)
        for record in state.get("vs_insurance_external_policies", [])
        if record.get("policy_id") != policy_id
    ]
    removed = len(external) != len(
        state.get("vs_insurance_external_policies", [])
    )
    state["vs_insurance_external_policies"] = external
    if removed:
        state["vs_insurance_links"] = [
            dict(link)
            for link in state.get("vs_insurance_links", [])
            if link.get("policy_id") != policy_id
        ]
    return removed


def source_label(source_type: object) -> str:
    return SOURCE_LABELS.get(str(source_type), "Source not verified — DEMO")


def verification_label(status: object) -> str:
    return VERIFICATION_LABELS.get(str(status), "Verification status not available")


__all__ = [
    "NOT_FOUND",
    "NOMINEE_LEGAL_WORDING",
    "PRODUCT_TYPES",
    "PROTOTYPE_LABEL",
    "active_nominee_link_for_policy",
    "all_policy_records",
    "derive_display_status",
    "display_date",
    "display_value",
    "ensure_insurance_session",
    "external_policies_for_user",
    "find_policy",
    "limited_shared_summary",
    "link_is_active",
    "link_is_visible_to_nominee",
    "mask_policy_number",
    "nominee_invitations_for_user",
    "nominee_status_label",
    "normalise_date",
    "owner_links_for_user",
    "paytm_policies_for_user",
    "paytm_record_from_fixture",
    "remove_external_policy_session",
    "reset_insurance_session",
    "seeded_paytm_records",
    "source_label",
    "verification_label",
]
