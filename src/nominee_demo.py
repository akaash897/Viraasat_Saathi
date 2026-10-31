"""Simulated Paytm-ID nominee linking.

No Paytm API, insurer API, authentication or legal nomination workflow is
implemented. A link is only created after explicit owner action, and policy
summary sharing is a separate opt-in that defaults to off.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.insurance_inventory import active_nominee_link_for_policy
from src.mock_paytm_data import timestamp_now

RELATIONSHIPS: dict[str, str] = {
    "spouse": "Spouse",
    "child": "Child",
    "parent": "Parent",
    "other": "Other",
}
RELATIONSHIP_OPTIONS = tuple(RELATIONSHIPS.keys())


class NomineeError(ValueError):
    """A safe, user-facing nominee workflow error."""


def _find_user(
    users: Sequence[Mapping[str, Any]], demo_user_id: str
) -> dict[str, Any] | None:
    needle = str(demo_user_id or "").strip().lower()
    for user in users:
        if str(user.get("demo_user_id", "")).lower() == needle:
            return dict(user)
    return None


def find_demo_user(
    users: Sequence[Mapping[str, Any]], demo_user_id: str
) -> dict[str, Any] | None:
    """Look up a nominee only in the seeded mock Paytm directory."""
    return _find_user(users, demo_user_id)


def relationship_label(value: object) -> str:
    return RELATIONSHIPS.get(str(value), "Other")


def can_manage_nominee(policy: Mapping[str, Any]) -> bool:
    source = str(policy.get("source_type", ""))
    if source == "PAYTM_DEMO":
        return True
    if source == "EXTERNAL_DOCUMENT":
        return policy.get("verification_status") == "USER_REVIEWED_UNVERIFIED"
    return False


def create_nominee_link(
    *,
    policy: Mapping[str, Any],
    owner_demo_user_id: str,
    nominee_demo_user_id: str,
    relationship: str,
    note: str,
    owner_confirmed: bool,
    share_summary: bool,
    users: Sequence[Mapping[str, Any]],
    existing_links: Sequence[Mapping[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create an explicitly authorised simulated nominee link.

    ``share_summary`` is intentionally independent of nomination and defaults
    to off at every call site.
    """
    if owner_confirmed is not True:
        raise NomineeError(
            "Explicit owner confirmation is required before a demo nominee link "
            "can be created."
        )
    if relationship not in RELATIONSHIPS:
        raise NomineeError("Choose a supported relationship.")
    if not can_manage_nominee(policy):
        raise NomineeError(
            "Review and confirm this external policy before adding a nominee."
        )

    owner = _find_user(users, owner_demo_user_id)
    nominee = _find_user(users, nominee_demo_user_id)
    if owner is None:
        raise NomineeError("The selected owner is not in the seeded demo directory.")
    if nominee is None:
        raise NomineeError(
            "That demo Paytm ID is not in the seeded mock directory. No lookup was "
            "sent to Paytm."
        )
    if owner["demo_user_id"] == nominee["demo_user_id"]:
        raise NomineeError("Choose a different demo user as the nominee.")
    if policy.get("owner_demo_user_id") != owner["demo_user_id"]:
        raise NomineeError("The selected policy does not belong to this demo user.")
    if active_nominee_link_for_policy(existing_links, str(policy["policy_id"])):
        raise NomineeError(
            "This policy already has a pending or accepted demo nominee link."
        )

    created = now or datetime.now().astimezone()
    created_iso = created.isoformat(timespec="seconds")
    cleaned_note = " ".join(str(note or "").split())[:300]
    return {
        "link_id": f"demo-link-{uuid4().hex}",
        "policy_id": str(policy["policy_id"]),
        "owner_demo_user_id": owner["demo_user_id"],
        "nominee_demo_user_id": nominee["demo_user_id"],
        "relationship": relationship,
        "note": cleaned_note,
        "owner_authorised_summary_sharing": bool(share_summary),
        "nominee_acceptance_status": "PENDING",
        "demo_link_status": "ACTIVE",
        "created_at": created_iso,
        "updated_at": created_iso,
    }


def respond_to_nominee_link(
    link: Mapping[str, Any],
    *,
    nominee_demo_user_id: str,
    accept: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Accept or decline a pending invitation as the invited demo user."""
    updated = dict(link)
    if updated.get("nominee_demo_user_id") != nominee_demo_user_id:
        raise NomineeError("Only the invited demo user can respond to this link.")
    if updated.get("demo_link_status") != "ACTIVE":
        raise NomineeError("This demo link is no longer active.")
    if updated.get("nominee_acceptance_status") != "PENDING":
        raise NomineeError("This demo invitation is no longer pending.")

    updated["nominee_acceptance_status"] = "ACCEPTED" if accept else "DECLINED"
    if not accept:
        updated["demo_link_status"] = "REVOKED"
    updated["updated_at"] = (
        now or datetime.now().astimezone()
    ).isoformat(timespec="seconds")
    return updated


def revoke_nominee_link(
    link: Mapping[str, Any],
    *,
    owner_demo_user_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Owner-side revoke of the demo sharing link, not an insurer nomination."""
    updated = dict(link)
    if updated.get("owner_demo_user_id") != owner_demo_user_id:
        raise NomineeError("Only the policy owner can revoke this demo link.")
    if updated.get("demo_link_status") == "REVOKED":
        return updated
    updated["demo_link_status"] = "REVOKED"
    updated["updated_at"] = (
        now or datetime.now().astimezone()
    ).isoformat(timespec="seconds")
    return updated


def replace_link(
    links: Sequence[Mapping[str, Any]], updated: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return a new link list with one record replaced by ``link_id``."""
    return [
        dict(updated) if link.get("link_id") == updated.get("link_id") else dict(link)
        for link in links
    ]


def link_created_message(link: Mapping[str, Any]) -> str:
    sharing = (
        "A limited summary is allowed after the nominee accepts."
        if link.get("owner_authorised_summary_sharing")
        else "Policy-summary sharing is off."
    )
    return (
        "Demo nominee link created with status AWAITING_DEMO_ACCEPTANCE. "
        f"{sharing} Insurer nomination has not been registered."
    )


__all__ = [
    "RELATIONSHIPS",
    "RELATIONSHIP_OPTIONS",
    "NomineeError",
    "can_manage_nominee",
    "create_nominee_link",
    "find_demo_user",
    "link_created_message",
    "relationship_label",
    "replace_link",
    "respond_to_nominee_link",
    "revoke_nominee_link",
]
