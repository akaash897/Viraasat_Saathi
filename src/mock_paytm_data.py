"""Seeded, fictional Paytm-style demo data.

This module is deliberately local-only. It contains **no network code**, no
Paytm SDK and no authentication. Every identity is a synthetic ``paytm.demo.*``
ID and every policy is a demo fixture whose insurer names are clearly fictional.

The fixtures are validated at load time so a malformed or accidentally
non-demo record fails fast instead of being rendered as if it were real.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MOCK_USERS_PATH = DATA_DIR / "mock_paytm_users.json"
MOCK_POLICIES_PATH = DATA_DIR / "mock_paytm_policies.json"
MOCK_NOMINEE_LINKS_PATH = DATA_DIR / "mock_nominee_links.json"

ProductType = Literal["health", "life", "motor", "travel", "other", "unknown"]
Relationship = Literal["spouse", "child", "parent", "other"]
AcceptanceStatus = Literal["PENDING", "ACCEPTED", "DECLINED"]
LinkStatus = Literal["ACTIVE", "REVOKED"]

DEMO_USER_PREFIX = "paytm.demo."
_REAL_IDENTIFIER_PATTERNS = (
    re.compile(r"\b[6-9]\d{9}\b"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _contains_real_identifier(value: str) -> bool:
    return any(pattern.search(value) for pattern in _REAL_IDENTIFIER_PATTERNS)


class MockPaytmUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demo_user_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    initials: str = Field(min_length=1, max_length=4)
    is_default: bool = False

    @field_validator("demo_user_id")
    @classmethod
    def _must_be_demo_id(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(DEMO_USER_PREFIX):
            raise ValueError("Paytm demo user ids must start with paytm.demo.")
        if _contains_real_identifier(value):
            raise ValueError("demo user ids must not contain real identifiers")
        return value

    @field_validator("display_name")
    @classmethod
    def _must_be_demo_name(cls, value: str) -> str:
        value = value.strip()
        if _contains_real_identifier(value):
            raise ValueError("demo display names must not contain real identifiers")
        return value


class MockPaytmPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1)
    owner_demo_user_id: str = Field(min_length=1)
    insurer_name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    product_type: ProductType
    policy_number_full: str = Field(min_length=1)
    policy_number_masked: str = Field(min_length=1)
    uin: str | None = None
    policy_start_date: date
    policy_end_date: date
    sum_insured: str | None = None
    premium_amount: str | None = None
    premium_frequency: str | None = None
    policyholder_name: str | None = None
    insured_persons: list[str] = Field(default_factory=list)
    source_type: Literal["PAYTM_DEMO"] = "PAYTM_DEMO"
    verification_status: Literal["SIMULATED_NOT_VERIFIED"] = (
        "SIMULATED_NOT_VERIFIED"
    )
    display_status: str = "Not verified with insurer"

    @field_validator("owner_demo_user_id")
    @classmethod
    def _owner_must_be_demo(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(DEMO_USER_PREFIX):
            raise ValueError("policy owner must be a paytm.demo user")
        return value

    @field_validator("policy_number_masked")
    @classmethod
    def _masked_number_must_be_masked(cls, value: str) -> str:
        value = value.strip()
        if value and not any(mark in value for mark in ("•", "*", "x", "X")):
            raise ValueError("seeded policy numbers must be masked")
        return value

    @model_validator(mode="after")
    def _date_order(self) -> "MockPaytmPolicy":
        if self.policy_end_date < self.policy_start_date:
            raise ValueError("policy end date must not precede start date")
        return self


class MockNomineeLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    owner_demo_user_id: str = Field(min_length=1)
    nominee_demo_user_id: str = Field(min_length=1)
    relationship: Relationship
    note: str = ""
    owner_authorised_summary_sharing: bool = False
    nominee_acceptance_status: AcceptanceStatus = "PENDING"
    demo_link_status: LinkStatus = "ACTIVE"
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)

    @field_validator("owner_demo_user_id", "nominee_demo_user_id")
    @classmethod
    def _links_must_be_demo(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(DEMO_USER_PREFIX):
            raise ValueError("nominee links must reference paytm.demo users")
        return value

    @model_validator(mode="after")
    def _no_self_link(self) -> "MockNomineeLink":
        if self.owner_demo_user_id == self.nominee_demo_user_id:
            raise ValueError("a demo user cannot nominate themselves")
        return self


class MockPaytmUserFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: list[MockPaytmUser] = Field(min_length=2)

    @model_validator(mode="after")
    def _ids_must_be_unique(self) -> "MockPaytmUserFixture":
        ids = [user.demo_user_id for user in self.users]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate demo user ids")
        if sum(1 for user in self.users if user.is_default) != 1:
            raise ValueError("exactly one demo user must be the default")
        return self


class MockPaytmPolicyFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policies: list[MockPaytmPolicy] = Field(min_length=2)

    @model_validator(mode="after")
    def _ids_must_be_unique(self) -> "MockPaytmPolicyFixture":
        ids = [policy.policy_id for policy in self.policies]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate mock policy ids")
        return self


class MockNomineeLinkFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    links: list[MockNomineeLink] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_must_be_unique(self) -> "MockNomineeLinkFixture":
        ids = [link.link_id for link in self.links]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate mock nominee link ids")
        return self


@lru_cache(maxsize=1)
def load_mock_paytm_users() -> tuple[MockPaytmUser, ...]:
    fixture = MockPaytmUserFixture.model_validate(_read_json(MOCK_USERS_PATH))
    return tuple(fixture.users)


@lru_cache(maxsize=1)
def load_mock_paytm_policies() -> tuple[MockPaytmPolicy, ...]:
    fixture = MockPaytmPolicyFixture.model_validate(_read_json(MOCK_POLICIES_PATH))
    users = {user.demo_user_id for user in load_mock_paytm_users()}
    for policy in fixture.policies:
        if policy.owner_demo_user_id not in users:
            raise ValueError(f"policy {policy.policy_id} references an unknown demo user")
    return tuple(fixture.policies)


@lru_cache(maxsize=1)
def load_seeded_nominee_links() -> tuple[MockNomineeLink, ...]:
    fixture = MockNomineeLinkFixture.model_validate(
        _read_json(MOCK_NOMINEE_LINKS_PATH)
    )
    users = {user.demo_user_id for user in load_mock_paytm_users()}
    policies = {policy.policy_id: policy for policy in load_mock_paytm_policies()}
    for link in fixture.links:
        if link.owner_demo_user_id not in users:
            raise ValueError(f"link {link.link_id} references an unknown owner")
        if link.nominee_demo_user_id not in users:
            raise ValueError(f"link {link.link_id} references an unknown nominee")
        policy = policies.get(link.policy_id)
        if policy is None:
            raise ValueError(f"link {link.link_id} references an unknown policy")
        if policy.owner_demo_user_id != link.owner_demo_user_id:
            raise ValueError(f"link {link.link_id} owner does not own the policy")
    return tuple(fixture.links)


def default_demo_user_id() -> str:
    users = load_mock_paytm_users()
    return next(user.demo_user_id for user in users if user.is_default)


def users_as_dicts() -> list[dict[str, object]]:
    return [user.model_dump(mode="json") for user in load_mock_paytm_users()]


def paytm_policies_as_dicts() -> list[dict[str, object]]:
    return [policy.model_dump(mode="json") for policy in load_mock_paytm_policies()]


def seeded_nominee_links_as_dicts() -> list[dict[str, object]]:
    return [link.model_dump(mode="json") for link in load_seeded_nominee_links()]


def demo_user_by_id(demo_user_id: str) -> dict[str, object] | None:
    needle = str(demo_user_id or "").strip().lower()
    for user in users_as_dicts():
        if str(user["demo_user_id"]).lower() == needle:
            return user
    return None


def timestamp_now() -> str:
    """Return an ISO timestamp without any document content."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
