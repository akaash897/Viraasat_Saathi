"""Shared safety constants and session helpers.

This module contains no network code and no persistence. The app's session
state is prefixed with ``vs_`` so Reset demo can clear every piece of temporary
case data without touching unrelated Streamlit state.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from decimal import Decimal
from urllib.parse import urlparse

SESSION_PREFIX = "vs_"

SAFETY_KEYS = (
    "privacy_banner",
    "claims_disclaimer",
    "checklist_validation_note",
    "anti_fraud_warning",
    "draft_no_submission",
    "lead_note",
    "not_searched_note",
    "no_portal_queried",
    "limitations_body",
)

# Terms that would turn a paraphrase into an adjudicative or legal statement.
# The optional Sarvam adapter rejects output containing these terms.
ADJUDICATIVE_TERMS = (
    "approved",
    "approval",
    "eligible",
    "eligibility",
    "guaranteed",
    "guarantee",
    "will be paid",
    "will pay",
    "entitled",
    "coverage confirmed",
    "settlement confirmed",
    "deadline",
    "legally",
)

OFFICIAL_LINK_NOTE = (
    "We have not searched this portal; open it to verify the lead."
)


def reset_session_state(state: MutableMapping[str, object]) -> int:
    """Remove every app-owned session key. Returns the number removed."""
    keys = [
        key
        for key in list(state.keys())
        if isinstance(key, str) and key.startswith(SESSION_PREFIX)
    ]
    for key in keys:
        del state[key]
    return len(keys)


def contains_adjudicative_claim(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ADJUDICATIVE_TERMS)


def is_official_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def format_inr(amount: Decimal | int | float | str) -> str:
    """Format a demo amount as INR without implying a real balance."""
    try:
        value = Decimal(str(amount))
    except Exception:
        return str(amount)
    return f"₹{value:,.2f}"
