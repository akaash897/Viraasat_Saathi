"""Preset local sign-in for the independent prototype.

This module is deliberately offline and mock-only. It contains no Paytm SDK,
network call, OTP flow or real credential store. The sign-in screen exists only
to demonstrate a personalised, logged-in experience with seeded fixture users.

The credentials below are local test fixtures. They are not Paytm credentials
and must never be reused for a real account.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from typing import Any

from src.mock_paytm_data import demo_user_by_id, users_as_dicts

# Login ID -> (password, seeded demo user). These values are intentionally
# obvious fixtures for the hackathon walkthrough.
_PRESET_ACCOUNTS: dict[str, dict[str, str]] = {
    "aarav": {
        "password": "aarav123",
        "demo_user_id": "paytm.demo.aarav",
    },
    "meera": {
        "password": "meera123",
        "demo_user_id": "paytm.demo.meera",
    },
}


def normalise_login_id(value: object) -> str:
    return str(value or "").strip().lower()


def login_id_for_user(demo_user_id: object) -> str:
    needle = str(demo_user_id or "").strip()
    for login_id, account in _PRESET_ACCOUNTS.items():
        if account["demo_user_id"] == needle:
            return login_id
    return ""


def authenticate(login_id: object, password: object) -> str | None:
    """Return the seeded demo user id for a matching fixture, else ``None``.

    The comparison is constant-time to avoid turning the preset login into a
    timing oracle, even though the accounts are local fixtures.
    """
    account = _PRESET_ACCOUNTS.get(normalise_login_id(login_id))
    if account is None:
        return None
    supplied = str(password or "")
    if not hmac.compare_digest(supplied, account["password"]):
        return None
    return account["demo_user_id"]


def preset_accounts() -> list[dict[str, Any]]:
    """Return display-safe preset accounts for the sign-in helper panel."""
    accounts: list[dict[str, Any]] = []
    for login_id, account in _PRESET_ACCOUNTS.items():
        user: Mapping[str, Any] | None = demo_user_by_id(account["demo_user_id"])
        if user is None:
            continue
        accounts.append(
            {
                "login_id": login_id,
                "password": account["password"],
                "demo_user_id": account["demo_user_id"],
                "display_name": str(user.get("display_name", login_id)),
                "initials": str(user.get("initials", login_id[:1].upper())),
            }
        )
    return accounts


def seeded_user_count() -> int:
    """Small convenience used by the sign-in panel copy."""
    return len(users_as_dicts())


__all__ = [
    "authenticate",
    "login_id_for_user",
    "normalise_login_id",
    "preset_accounts",
    "seeded_user_count",
]
