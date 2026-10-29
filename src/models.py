"""Typed data structures for Virasat Saathi.

The models are deliberately strict: the demo fixtures are validated at load
time, and the fictional notice must be true. No model here is used to persist
user data to disk.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Language = Literal["en", "hi"]
ClaimType = Literal["health_reimbursement"]
PatternStrength = Literal["low", "medium", "strong_pattern"]
RuleKey = Literal["single_clue", "same_month_multiple", "recurring_pattern"]
DraftKind = Literal[
    "missing_document_followup",
    "claim_status",
    "additional_information",
    "grievance_preparation",
]
ChecklistStatus = Literal["not_marked", "marked_provided", "needs_confirmation"]


class PolicyClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    page: int = Field(ge=1)
    heading: str = Field(min_length=1)
    text: str = Field(min_length=1)


class PolicyFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    statement_en: str = Field(min_length=1)
    statement_hi: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    page: int = Field(ge=1)


class DemoPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_name: str = Field(min_length=1)
    insurer_label: str = Field(min_length=1)
    policy_label: str = Field(min_length=1)
    currency: Literal["INR"]
    fictional_notice: bool
    notice_en: str = Field(min_length=1)
    notice_hi: str = Field(min_length=1)
    clauses: list[PolicyClause] = Field(min_length=1)
    facts: list[PolicyFact] = Field(min_length=1)

    @field_validator("fictional_notice")
    @classmethod
    def _must_be_fictional(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("demo policy must be marked fictional")
        return value

    @model_validator(mode="after")
    def _citations_must_exist(self) -> "DemoPolicy":
        clauses = {clause.id: clause for clause in self.clauses}
        if len(clauses) != len(self.clauses):
            raise ValueError("duplicate clause ids in demo policy")
        for fact in self.facts:
            clause = clauses.get(fact.clause_id)
            if clause is None:
                raise ValueError(f"fact {fact.id} cites unknown clause {fact.clause_id}")
            if clause.page != fact.page:
                raise ValueError(
                    f"fact {fact.id} page {fact.page} does not match clause page {clause.page}"
                )
        return self

    def clause_by_id(self, clause_id: str) -> PolicyClause | None:
        return next((clause for clause in self.clauses if clause.id == clause_id), None)

    def fact_by_topic(self, topic: str) -> PolicyFact | None:
        return next((fact for fact in self.facts if fact.topic == topic), None)

    def facts_by_topic(self) -> dict[str, PolicyFact]:
        return {fact.topic: fact for fact in self.facts}


class ChecklistCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label_en: str = Field(min_length=1)
    label_hi: str = Field(min_length=1)
    why_en: str = Field(min_length=1)
    why_hi: str = Field(min_length=1)
    source_clause_id: str = Field(min_length=1)
    source_page: int = Field(ge=1)
    needs_confirmation: bool = False


class TimelineStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    stage_en: str = Field(min_length=1)
    stage_hi: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    description_hi: str = Field(min_length=1)
    status: Literal["not_started"] = "not_started"


class DemoClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    product: Literal["health_insurance"]
    claim_type: ClaimType
    claim_status: str = Field(min_length=1)
    claim_status_label_en: str = Field(min_length=1)
    claim_status_label_hi: str = Field(min_length=1)
    claimant_label: str = Field(min_length=1)
    claimant_label_hi: str = Field(min_length=1)
    policy_label: str = Field(min_length=1)
    policy_label_hi: str = Field(min_length=1)
    hospital_label: str = Field(min_length=1)
    hospital_label_hi: str = Field(min_length=1)
    checklist_source_id: str = Field(min_length=1)
    fictional_notice: bool
    notice_en: str = Field(min_length=1)
    notice_hi: str = Field(min_length=1)
    required_document_categories: list[ChecklistCategory] = Field(min_length=1)
    timeline: list[TimelineStep] = Field(min_length=1)

    @field_validator("fictional_notice")
    @classmethod
    def _must_be_fictional(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("demo claim must be marked fictional")
        return value

    @model_validator(mode="after")
    def _ids_must_be_unique(self) -> "DemoClaim":
        category_ids = [item.id for item in self.required_document_categories]
        if len(set(category_ids)) != len(category_ids):
            raise ValueError("duplicate checklist category ids")
        step_ids = [step.id for step in self.timeline]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("duplicate timeline step ids")
        return self

    @property
    def total_document_categories(self) -> int:
        return len(self.required_document_categories)

    def category_by_id(self, category_id: str) -> ChecklistCategory | None:
        return next(
            (item for item in self.required_document_categories if item.id == category_id),
            None,
        )


class TransactionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_number: int = Field(ge=2)
    date: date
    description: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    direction: Literal["debit", "credit"]

    @field_validator("description")
    @classmethod
    def _description_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("description cannot be blank")
        return value


class EvidenceRow(BaseModel):
    """An exact, unmodified source row shown as evidence for a lead."""

    model_config = ConfigDict(extra="forbid")

    row_number: int
    date: date
    description: str
    amount: Decimal
    direction: Literal["debit", "credit"]


class Lead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str = Field(min_length=1)
    category_id: Literal[
        "possible_insurance_payment",
        "possible_investment_or_sip",
        "possible_lender_or_emi",
        "possible_recurring_subscription",
    ]
    merchant_key: str = Field(min_length=1)
    pattern_strength: PatternStrength
    is_recurring: bool
    distinct_months: int = Field(ge=1)
    matched_keyword: str = Field(min_length=1)
    evidence: list[EvidenceRow] = Field(min_length=1)
    rule_key: RuleKey
    rule_en: str = Field(min_length=1)
    rule_hi: str = Field(min_length=1)
    does_not_prove_en: str = Field(min_length=1)
    does_not_prove_hi: str = Field(min_length=1)
    next_step_en: str = Field(min_length=1)
    next_step_hi: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class PolicyAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    verified: bool
    statement_en: str = Field(min_length=1)
    statement_hi: str = Field(min_length=1)
    clause_id: str | None = None
    page: int | None = None
    source_label: str = "Not verified in the available information"

    @model_validator(mode="after")
    def _verified_answers_need_citation(self) -> "PolicyAnswer":
        if self.verified and (not self.clause_id or self.page is None):
            raise ValueError("verified policy answers must carry a clause id and page")
        return self


class ChecklistProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    marked: int = Field(ge=0)
    remaining: int = Field(ge=0)
    needs_confirmation: int = Field(ge=0)
    insurer_validated: Literal[False] = False


class SourceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    checked_on: str = Field(min_length=1)
    notes: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def _must_be_https(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("official source URLs must use https")
        return value


class SourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registry_note_en: str = Field(min_length=1)
    registry_note_hi: str = Field(min_length=1)
    sources: list[SourceEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_must_be_unique(self) -> "SourceRegistry":
        ids = [source.id for source in self.sources]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate source ids")
        return self

    def by_id(self, source_id: str) -> SourceEntry | None:
        return next((source for source in self.sources if source.id == source_id), None)

    def by_ids(self, source_ids: list[str]) -> list[SourceEntry]:
        return [source for source in self.sources if source.id in source_ids]
