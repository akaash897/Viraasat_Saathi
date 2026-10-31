"""Deterministic family claim orchestration for the Phase 2+ prototype.

This module implements pure, testable rules for:
- Policy/event relevance matrix
- Family claim batch and child workflow management
- Common document indexing
- Playbook retrieval

No LLM decisions, no network calls, no authentication.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from src.insurance_inventory import seeded_paytm_records, find_policy
from src.mock_paytm_data import demo_user_by_id
from src.nominee_consistency import load_linked_profiles

# ----- Types -----

EventRelevance = Literal[
    "POTENTIAL_LIFE_DEATH_CLAIM",
    "POTENTIAL_ACCIDENTAL_DEATH_BENEFIT",
    "CREDIT_LIFE_ENQUIRY",
    "OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY",
    "MOTOR_ACCIDENT_COVER_REVIEW",
    "NOT_INDICATED_BY_AVAILABLE_RECORDS",
    "INSUFFICIENT_EVIDENCE",
]

ClaimantCapacity = Literal[
    "RECORDED_NOMINEE_IN_DEMO",
    "AUTHORISED_REPRESENTATIVE_DEMO",
    "LEGAL_HEIR_CLAIMANT_UNVERIFIED",
    "OTHER",
    "UNSURE",
]

WorkflowState = Literal[
    "DISCOVERED",
    "RELEVANCE_REVIEW",
    "CHECKLIST_READY",
    "DOCUMENTS_IN_PROGRESS",
    "READY_FOR_USER_REVIEW",
    "DRAFT_PREPARED",
    "USER_MARKED_SUBMITTED",
    "FOLLOW_UP",
    "USER_MARKED_RESOLVED",
    "INSURER_QUERY_RECORDED",
]

# ----- Event Relevance Rules -----

def classify_policy_event_relevance(
    policy: Mapping[str, Any],
    event_type: str,
    event_date: date,
    deceased_demo_user_id: str,
    family_case_docs: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[EventRelevance, list[dict[str, Any]]]:
    """
    Deterministic policy/event relevance classification.

    Returns (relevance, evidence_list)
    """
    if event_type != "DEATH":
        return ("INSUFFICIENT_EVIDENCE", [{"label": "Event type", "value": event_type, "source": "FAMILY_CASE"}])

    product_type = str(policy.get("product_type", "unknown")).lower()
    policy_id = str(policy.get("policy_id", ""))
    insured_persons = list(policy.get("insured_persons", []))
    policyholder = str(policy.get("policyholder_name", ""))

    evidence = [
        {"label": "Policy ID", "value": policy_id, "source": "POLICY_RECORD"},
        {"label": "Product type", "value": product_type, "source": "POLICY_RECORD"},
        {"label": "Policyholder", "value": policyholder, "source": "POLICY_RECORD"},
        {"label": "Insured persons", "value": ", ".join(insured_persons), "source": "POLICY_RECORD"},
        {"label": "Event date", "value": str(event_date), "source": "FAMILY_CASE"},
    ]

    # Check if deceased matches insured/policyholder
    # We need to map demo_user_id to display name
    deceased_display = ""
    if deceased_demo_user_id:
        deceased_user = demo_user_by_id(deceased_demo_user_id)
        if deceased_user:
            deceased_display = str(deceased_user.get("display_name", ""))

    deceased_matches_insured = deceased_display in insured_persons
    deceased_matches_policyholder = deceased_display == policyholder

    # Check policy period
    start = policy.get("policy_start_date")
    end = policy.get("policy_end_date")
    policy_active = False
    if start and end:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
            policy_active = start_date <= event_date <= end_date
        except ValueError:
            pass
    evidence.append({"label": "Policy active at event date", "value": str(policy_active), "source": "POLICY_RECORD"})

    # 1. Life insurance
    if product_type == "life":
        if deceased_matches_insured and policy_active:
            return ("POTENTIAL_LIFE_DEATH_CLAIM", evidence + [
                {"label": "Deceased matches life insured", "value": "Yes", "source": "POLICY_RECORD"},
            ])
        return ("NOT_INDICATED_BY_AVAILABLE_RECORDS", evidence + [
            {"label": "Deceased matches life insured", "value": "No", "source": "POLICY_RECORD"},
        ])

    # 2. Personal accident
    if product_type == "personal_accident":
        # Check if accidental death cover exists (simplified: check if product name suggests it)
        prod_name = str(policy.get("product_name", "")).lower()
        has_accidental_death = "accident" in prod_name or "personal accident" in prod_name
        if has_accidental_death and deceased_matches_insured and policy_active:
            return ("POTENTIAL_ACCIDENTAL_DEATH_BENEFIT", evidence + [
                {"label": "Accidental death cover present", "value": "Yes (inferred)", "source": "POLICY_RECORD"},
            ])
        return ("NOT_INDICATED_BY_AVAILABLE_RECORDS", evidence + [
            {"label": "Accidental death cover present", "value": "Not confirmed in fixture", "source": "POLICY_RECORD"},
        ])

    # 3. Credit life / loan protection
    if product_type == "credit_life" or "credit" in product_type:
        if deceased_matches_policyholder and policy_active:
            # Check for loan assignment indicator in fixture
            has_assignment = bool(policy.get("loan_reference") or policy.get("lender_name"))
            return ("CREDIT_LIFE_ENQUIRY", evidence + [
                {"label": "Deceased is policyholder", "value": "Yes", "source": "POLICY_RECORD"},
                {"label": "Loan assignment indicator", "value": "Yes" if has_assignment else "Not in fixture", "source": "POLICY_RECORD"},
            ])
        return ("NOT_INDICATED_BY_AVAILABLE_RECORDS", evidence)

    # 4. Health insurance
    if product_type == "health":
        # Check if there are outstanding medical expenses (simulated via family case docs)
        has_outstanding_expenses = False
        if family_case_docs:
            for doc in family_case_docs:
                if str(doc.get("category", "")).lower() in {"hospital_bill", "medical_expense", "treatment_bill"}:
                    has_outstanding_expenses = True
                    break
        if has_outstanding_expenses and policy_active:
            return ("OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY", evidence + [
                {"label": "Outstanding medical expenses found", "value": "Yes", "source": "FAMILY_CASE_DOCS"},
            ])
        return ("NOT_INDICATED_BY_AVAILABLE_RECORDS", evidence + [
            {"label": "Outstanding medical expenses found", "value": "No (no seeded expense docs)", "source": "FAMILY_CASE_DOCS"},
        ])

    # 5. Motor insurance
    if product_type == "motor":
        # Check for owner-driver PA cover
        prod_name = str(policy.get("product_name", "")).lower()
        has_owner_driver_pa = "owner" in prod_name and "driver" in prod_name and "accident" in prod_name
        # Also check if accident evidence exists in family case docs
        has_accident_evidence = False
        if family_case_docs:
            for doc in family_case_docs:
                if str(doc.get("category", "")).lower() in {"accident_report", "fir", "post_mortem"}:
                    has_accident_evidence = True
                    break
        if has_owner_driver_pa and has_accident_evidence and policy_active:
            return ("MOTOR_ACCIDENT_COVER_REVIEW", evidence + [
                {"label": "Owner-driver PA cover", "value": "Yes (inferred)", "source": "POLICY_RECORD"},
                {"label": "Accident evidence in case", "value": "Yes", "source": "FAMILY_CASE_DOCS"},
            ])
        return ("NOT_INDICATED_BY_AVAILABLE_RECORDS", evidence + [
            {"label": "Owner-driver PA cover", "value": "Not confirmed in fixture", "source": "POLICY_RECORD"},
            {"label": "Accident evidence in case", "value": "No (no seeded accident docs)", "source": "FAMILY_CASE_DOCS"},
        ])

    # 6. Other/unknown
    return ("INSUFFICIENT_EVIDENCE", evidence + [
        {"label": "Product type", "value": product_type, "source": "POLICY_RECORD"},
    ])


# ----- Playbook Retrieval -----

def load_playbook(playbook_id: str) -> dict[str, Any] | None:
    """Load a claim playbook from JSON fixture."""
    path = Path(__file__).resolve().parent.parent / "data" / "claim_playbooks" / f"{playbook_id}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_playbook_for_relevance(relevance: EventRelevance, product_type: str) -> str | None:
    """Map event relevance and product type to playbook ID."""
    mapping: dict[tuple[EventRelevance, str], str] = {
        ("POTENTIAL_LIFE_DEATH_CLAIM", "life"): "life_death_demo_v1",
        ("POTENTIAL_ACCIDENTAL_DEATH_BENEFIT", "personal_accident"): "personal_accident_death_demo_v1",
        ("CREDIT_LIFE_ENQUIRY", "credit_life"): "credit_life_enquiry_demo_v1",
        ("OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY", "health"): "health_outstanding_expense_demo_v1",
        ("MOTOR_ACCIDENT_COVER_REVIEW", "motor"): "motor_accident_review_demo_v1",
    }
    return mapping.get((relevance, product_type))


# ----- Data Structures -----

@dataclass(frozen=True)
class PolicyRelevanceResult:
    policy_id: str
    product_type: str
    insurer_name: str
    event_relevance: EventRelevance
    evidence: tuple[dict[str, Any], ...]
    nominee_name: str | None
    nomination_status: str
    claimant_capacity: ClaimantCapacity
    playbook_id: str | None


@dataclass
class PolicyClaimWorkflow:
    workflow_id: str
    batch_id: str
    policy_id: str
    event_relevance: EventRelevance
    relevance_evidence: list[dict[str, Any]]
    claimant_capacity: ClaimantCapacity
    claimant_capacity_verification: Literal["UNVERIFIED_BY_INSURER"] = "UNVERIFIED_BY_INSURER"
    playbook_id: str | None = None
    documents: list[dict[str, Any]] = field(default_factory=list)
    status: WorkflowState = "CHECKLIST_READY"
    timeline: list[dict[str, Any]] = field(default_factory=list)
    draft_text: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "batch_id": self.batch_id,
            "policy_id": self.policy_id,
            "event_relevance": self.event_relevance,
            "relevance_evidence": self.relevance_evidence,
            "claimant_capacity": self.claimant_capacity,
            "claimant_capacity_verification": self.claimant_capacity_verification,
            "playbook_id": self.playbook_id,
            "documents": self.documents,
            "status": self.status,
            "timeline": self.timeline,
            "draft_text": self.draft_text,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyClaimWorkflow":
        return cls(**data)


@dataclass
class FamilyClaimBatch:
    batch_id: str
    family_case_id: str
    claimant_demo_user_id: str
    deceased_demo_user_id: str
    event_type: str
    event_date: str
    access_status: Literal["SIMULATED_ACCESS_GRANTED"]
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"]
    child_workflow_ids: list[str]
    created_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "family_case_id": self.family_case_id,
            "claimant_demo_user_id": self.claimant_demo_user_id,
            "deceased_demo_user_id": self.deceased_demo_user_id,
            "event_type": self.event_type,
            "event_date": self.event_date,
            "access_status": self.access_status,
            "status": self.status,
            "child_workflow_ids": self.child_workflow_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FamilyClaimBatch":
        return cls(**data)


# ----- Session State Helpers -----

CLAIM_BATCH_PREFIX = "vs_claim_batch_"
CLAIM_WORKFLOW_PREFIX = "vs_claim_workflow_"
COMMON_DOC_PREFIX = "vs_common_doc_"


def get_batches(state: Mapping[str, Any]) -> list[FamilyClaimBatch]:
    batches = []
    for key, value in state.items():
        if key.startswith(CLAIM_BATCH_PREFIX) and isinstance(value, Mapping):
            batches.append(FamilyClaimBatch.from_dict(dict(value)))
    return batches


def get_workflows(state: Mapping[str, Any]) -> list[PolicyClaimWorkflow]:
    workflows = []
    for key, value in state.items():
        if key.startswith(CLAIM_WORKFLOW_PREFIX) and isinstance(value, Mapping):
            workflows.append(PolicyClaimWorkflow.from_dict(dict(value)))
    return workflows


def get_common_documents(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    docs = []
    for key, value in state.items():
        if key.startswith(COMMON_DOC_PREFIX) and isinstance(value, Mapping):
            docs.append(dict(value))
    return docs


def create_family_claim_batch(
    state: dict[str, Any],
    family_case_id: str,
    claimant_demo_user_id: str,
    deceased_demo_user_id: str,
    event_type: str,
    event_date: date,
    selected_policy_ids: Sequence[str],
) -> FamilyClaimBatch:
    """Create a family claim batch and child workflows. Returns the batch."""
    batch_id = f"batch-{uuid.uuid4().hex[:12]}"
    workflow_ids: list[str] = []

    policies = seeded_paytm_records()
    policy_map = {p["policy_id"]: p for p in policies}

    # Determine claimant capacity for each policy
    for policy_id in selected_policy_ids:
        policy = policy_map.get(policy_id)
        if not policy:
            continue

        # Determine claimant capacity based on nominee links
        capacity: ClaimantCapacity = "UNSURE"
        if policy.get("ocr_nominee_name") and claimant_demo_user_id in str(policy.get("ocr_nominee_name", "")).lower():
            capacity = "RECORDED_NOMINEE_IN_DEMO"
        elif policy.get("policyholder_name") and claimant_demo_user_id in str(policy.get("policyholder_name", "")).lower():
            capacity = "AUTHORISED_REPRESENTATIVE_DEMO"

        relevance, evidence = classify_policy_event_relevance(
            policy, event_type, event_date, deceased_demo_user_id, []
        )
        playbook_id = get_playbook_for_relevance(relevance, policy.get("product_type", "unknown"))

        workflow_id = f"wf-{uuid.uuid4().hex[:12]}"
        workflow = PolicyClaimWorkflow(
            workflow_id=workflow_id,
            batch_id=batch_id,
            policy_id=policy_id,
            event_relevance=relevance,
            relevance_evidence=evidence,
            claimant_capacity=capacity,
            playbook_id=playbook_id,
        )
        state[f"{CLAIM_WORKFLOW_PREFIX}{workflow_id}"] = workflow.to_dict()
        workflow_ids.append(workflow_id)

    batch = FamilyClaimBatch(
        batch_id=batch_id,
        family_case_id=family_case_id,
        claimant_demo_user_id=claimant_demo_user_id,
        deceased_demo_user_id=deceased_demo_user_id,
        event_type=event_type,
        event_date=event_date.isoformat(),
        access_status="SIMULATED_ACCESS_GRANTED",
        status="ACTIVE",
        child_workflow_ids=workflow_ids,
    )
    state[f"{CLAIM_BATCH_PREFIX}{batch_id}"] = batch.to_dict()
    return batch


def add_common_document(
    state: dict[str, Any],
    batch_id: str,
    category: str,
    file_name: str,
    mime_type: str,
    extracted_fields: dict[str, Any] | None = None,
) -> str:
    """Add a document to the common document index for a family claim batch."""
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    doc = {
        "doc_id": doc_id,
        "batch_id": batch_id,
        "category": category,
        "file_name": file_name,
        "mime_type": mime_type,
        "extracted_fields": extracted_fields or {},
        "mapped_workflow_ids": [],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    state[f"{COMMON_DOC_PREFIX}{doc_id}"] = doc
    return doc_id


def map_document_to_workflow(
    state: dict[str, Any],
    doc_id: str,
    workflow_id: str,
) -> bool:
    """Map a common document to a specific child workflow."""
    key = f"{COMMON_DOC_PREFIX}{doc_id}"
    if key not in state:
        return False
    doc = state[key]
    mapped = list(doc.get("mapped_workflow_ids", []))
    if workflow_id not in mapped:
        mapped.append(workflow_id)
        doc["mapped_workflow_ids"] = mapped
        state[key] = doc
    return True


def add_workflow_timeline_event(
    state: dict[str, Any],
    workflow_id: str,
    event_type: str,
    event_date: date,
    note: str,
    user_reported: bool = True,
) -> bool:
    """Add a timeline event to a workflow."""
    key = f"{CLAIM_WORKFLOW_PREFIX}{workflow_id}"
    if key not in state:
        return False
    workflow = state[key]
    timeline = list(workflow.get("timeline", []))
    timeline.append({
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "event_type": event_type,
        "event_date": event_date.isoformat(),
        "note": note,
        "user_reported": user_reported,
        "source": "USER_REPORTED" if user_reported else "SIMULATED",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    workflow["timeline"] = timeline
    workflow["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    state[key] = workflow
    return True


def save_workflow_draft(
    state: dict[str, Any],
    workflow_id: str,
    draft_text: str,
) -> bool:
    """Save an editable draft for a workflow."""
    key = f"{CLAIM_WORKFLOW_PREFIX}{workflow_id}"
    if key not in state:
        return False
    workflow = state[key]
    workflow["draft_text"] = draft_text
    workflow["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    state[key] = workflow
    return True


def update_workflow_status(
    state: dict[str, Any],
    workflow_id: str,
    status: WorkflowState,
) -> bool:
    """Update workflow status."""
    key = f"{CLAIM_WORKFLOW_PREFIX}{workflow_id}"
    if key not in state:
        return False
    workflow = state[key]
    workflow["status"] = status
    workflow["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    state[key] = workflow
    return True


# ----- Sarvam-105B Explanation Schema -----

class SarvamClaimOrchestratorSchema:
    """Schema for Sarvam-105B structured output for claim orchestrator explanations."""

    PORTFOLIO_SUMMARY_SCHEMA = {
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


__all__ = [
    "EventRelevance",
    "ClaimantCapacity",
    "WorkflowState",
    "classify_policy_event_relevance",
    "load_playbook",
    "get_playbook_for_relevance",
    "PolicyRelevanceResult",
    "PolicyClaimWorkflow",
    "FamilyClaimBatch",
    "create_family_claim_batch",
    "get_batches",
    "get_workflows",
    "get_common_documents",
    "add_common_document",
    "map_document_to_workflow",
    "add_workflow_timeline_event",
    "save_workflow_draft",
    "update_workflow_status",
    "SarvamClaimOrchestratorSchema",
]