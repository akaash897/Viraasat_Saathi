"""Deterministic nominee consistency analysis for the Phase 2+ prototype.

This module implements pure, testable comparison rules for nominee data across
policies and against consented mock linked profiles. No LLM calls, no network,
no authentication. All findings are machine-readable and auditable.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from src.insurance_inventory import normalise_date, seeded_paytm_records
from src.mock_paytm_data import load_mock_paytm_users

# ----- Finding codes and severity -----

FindingCode = Literal[
    "NAME_VARIATION_REVIEW",
    "POSSIBLE_NAME_MISMATCH",
    "DOB_MISMATCH_REVIEW",
    "DOB_NOT_AVAILABLE",
    "RELATIONSHIP_MISMATCH_REVIEW",
    "MINOR_NOMINEE_APPOINTEE_REVIEW",
    "APPOINTEE_DETAILS_UNVERIFIED",
    "AGE_STATUS_UNKNOWN",
    "NOMINEE_SHARE_TOTAL_REVIEW",
    "NOMINATION_NOT_FOUND_IN_UPLOADED_DOCUMENT",
    "INSURER_REGISTRATION_NOT_CONFIRMED",
    "DIFFERENT_NOMINEES_ACROSS_POLICIES",
    "PROFILE_DETAILS_NOT_SHARED",
    "PRODUCT_RULE_CONFIRMATION_REQUIRED",
]

Severity = Literal["INFO", "ATTENTION", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class EvidenceItem:
    label: str
    value: str
    source: str  # e.g., "POLICY_OCR", "MOCK_LINKED_PROFILE", "FAMILY_CASE", "USER_ENTERED"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    policy_id: str
    finding_code: FindingCode
    severity: Severity
    status: Literal["OPEN", "REVIEWED", "CLOSED"]
    summary: str
    evidence: tuple[EvidenceItem, ...]
    explanation_key: str
    recommended_user_action: str
    requires_human_review: bool


# ----- Normalisation helpers -----

def normalise_name_for_comparison(value: str) -> str:
    """Unicode-normalise, case-fold, strip punctuation/honorifics for comparison."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    text = text.strip()
    # Remove common honorifics and punctuation for comparison
    text = re.sub(r"[\.\,\-\_\'\"]", " ", text)
    text = re.sub(r"\b(mr|mrs|ms|dr|prof|shri|smt|kumari)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def name_similarity(a: str, b: str) -> float:
    """Return a similarity ratio between 0 and 1 using SequenceMatcher."""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, normalise_name_for_comparison(a), normalise_name_for_comparison(b)).ratio()


def parse_dob(value: object) -> date | None:
    """Parse a date of birth from various formats. Return None if ambiguous."""
    if value is None:
        return None
    iso = normalise_date(value)
    if iso is None:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def calculate_age(dob: date, as_of: date) -> int:
    """Calculate age at a reference date."""
    years = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        years -= 1
    return years


# ----- Core comparison functions -----

def compare_nominee_name(
    policy_nominee_name: str | None,
    profile_legal_name: str | None,
    profile_display_name: str | None,
) -> tuple[FindingCode | None, float]:
    """
    Compare nominee name from policy with linked profile names.
    Returns (finding_code, similarity_score) where finding_code is None if exact match.
    """
    policy_norm = normalise_name_for_comparison(policy_nominee_name or "")
    legal_norm = normalise_name_for_comparison(profile_legal_name or "")
    display_norm = normalise_name_for_comparison(profile_display_name or "")

    if not policy_norm:
        return ("DOB_NOT_AVAILABLE", 0.0)  # Caller should handle missing policy name

    # Check exact match against legal name first, then display name
    if policy_norm == legal_norm or policy_norm == display_norm:
        return (None, 1.0)

    # Fuzzy match
    legal_score = name_similarity(policy_nominee_name or "", profile_legal_name or "")
    display_score = name_similarity(policy_nominee_name or "", profile_display_name or "")
    best_score = max(legal_score, display_score)

    if best_score >= 0.9:
        return ("NAME_VARIATION_REVIEW", best_score)
    if best_score >= 0.7:
        return ("POSSIBLE_NAME_MISMATCH", best_score)
    return ("POSSIBLE_NAME_MISMATCH", best_score)


def compare_dob(
    policy_dob: str | None,
    profile_dob: str | None,
) -> FindingCode | None:
    """Compare dates of birth. Return finding code if mismatch or missing."""
    pol = parse_dob(policy_dob)
    prof = parse_dob(profile_dob)

    if pol is None and prof is None:
        return "DOB_NOT_AVAILABLE"
    if pol is None or prof is None:
        return "DOB_NOT_AVAILABLE"
    if pol != prof:
        return "DOB_MISMATCH_REVIEW"
    return None


def compare_relationship(
    policy_relationship: str | None,
    profile_relationship: str | None,
) -> FindingCode | None:
    """Compare relationship if both are explicitly present."""
    if not policy_relationship or not profile_relationship:
        return None
    pol = str(policy_relationship).strip().upper()
    prof = str(profile_relationship).strip().upper()
    if pol != prof:
        return "RELATIONSHIP_MISMATCH_REVIEW"
    return None


def check_minor_nominee(
    nominee_dob: str | None,
    event_date: date | None,
    product_type: str,
    appointee_name: str | None,
    appointee_relationship: str | None,
) -> FindingCode | None:
    """
    Check for minor nominee on life policy with missing appointee.
    Returns finding code if review needed.
    """
    if product_type != "life":
        return "PRODUCT_RULE_CONFIRMATION_REQUIRED"

    dob = parse_dob(nominee_dob)
    if dob is None or event_date is None:
        return "AGE_STATUS_UNKNOWN"

    age = calculate_age(dob, event_date)
    if age < 18:
        if not appointee_name and not appointee_relationship:
            return "MINOR_NOMINEE_APPOINTEE_REVIEW"
        return "APPOINTEE_DETAILS_UNVERIFIED"
    return None


def check_allocation_total(
    nominees: Sequence[Mapping[str, Any]],
) -> FindingCode | None:
    """Check if nominee shares total 100% when explicit percentages are present."""
    total = 0
    has_shares = False
    for nom in nominees:
        share = nom.get("nominee_share_percent")
        if share is not None:
            try:
                total += float(share)
                has_shares = True
            except (TypeError, ValueError):
                pass
    if has_shares and abs(total - 100.0) > 0.01:
        return "NOMINEE_SHARE_TOTAL_REVIEW"
    return None


def check_insurer_registration_status(record: Mapping[str, Any]) -> FindingCode | None:
    """Determine if insurer registration is unconfirmed."""
    status = str(record.get("verification_status", ""))
    if status in {"SIMULATED_NOT_VERIFIED", "OCR_EXTRACTED_NEEDS_REVIEW", "USER_REVIEWED_UNVERIFIED"}:
        return "INSURER_REGISTRATION_NOT_CONFIRMED"
    return None


# ----- Main analysis function -----

def analyse_portfolio(
    *,
    owner_demo_user_id: str,
    event_date: date | None = None,
    linked_profiles: Sequence[Mapping[str, Any]] | None = None,
    nominee_links: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[Finding], dict[str, Any]]:
    """
    Run deterministic nominee consistency analysis for a user's policy portfolio.

    Returns (findings, portfolio_summary)
    """
    if linked_profiles is None:
        linked_profiles = load_linked_profiles()

    # Load policies for the owner
    policies = seeded_paytm_records()
    user_policies = [p for p in policies if p.get("owner_demo_user_id") == owner_demo_user_id]

    # Build profile lookup by demo_user_id
    profile_by_id = {p["demo_paytm_user_id"]: p for p in linked_profiles}

    findings: list[Finding] = []
    finding_counter = 0

    def add_finding(
        policy_id: str,
        code: FindingCode,
        severity: Severity,
        summary: str,
        evidence: list[EvidenceItem],
        explanation_key: str,
        recommended_action: str,
    ) -> None:
        nonlocal finding_counter
        finding_counter += 1
        findings.append(Finding(
            finding_id=f"find_{finding_counter:03d}",
            policy_id=policy_id,
            finding_code=code,
            severity=severity,
            status="OPEN",
            summary=summary,
            evidence=tuple(evidence),
            explanation_key=explanation_key,
            recommended_user_action=recommended_action,
            requires_human_review=True,
        ))

    for policy in user_policies:
        policy_id = str(policy.get("policy_id", ""))
        product_type = str(policy.get("product_type", "unknown"))
        nominee_name = policy.get("ocr_nominee_name") or policy.get("policyholder_name")
        nominee_dob = policy.get("ocr_nominee_dob")
        nominee_relationship = policy.get("ocr_nominee_relationship")
        nominee_share = policy.get("nominee_share_percent")
        appointee_name = policy.get("guardian_or_appointee_name")
        appointee_relationship = policy.get("guardian_or_appointee_relationship")

        # Find linked profile via nominee links
        linked_profile = None
        if nominee_links:
            for link in nominee_links:
                if (link.get("policy_id") == policy_id
                        and link.get("nominee_acceptance_status") == "ACCEPTED"
                        and link.get("owner_authorised_summary_sharing")
                        and link.get("demo_link_status") == "ACTIVE"):
                    nominee_user_id = link.get("nominee_demo_user_id")
                    if nominee_user_id:
                        linked_profile = profile_by_id.get(nominee_user_id)
                        break

        # 1. Name comparison
        if linked_profile and nominee_name:
            code, score = compare_nominee_name(
                nominee_name,
                linked_profile.get("legal_name_demo"),
                linked_profile.get("display_name"),
            )
            if code:
                ev = [
                    EvidenceItem("Name on policy (OCR/record)", str(nominee_name), "POLICY_OCR"),
                    EvidenceItem("Legal name on linked demo profile", str(linked_profile.get("legal_name_demo")), "MOCK_LINKED_PROFILE"),
                ]
                if linked_profile.get("display_name") != linked_profile.get("legal_name_demo"):
                    ev.append(EvidenceItem("Display name on linked demo profile", str(linked_profile.get("display_name")), "MOCK_LINKED_PROFILE"))
                sev: Severity = "ATTENTION" if code == "NAME_VARIATION_REVIEW" else "REVIEW_REQUIRED"
                add_finding(
                    policy_id, code, sev,
                    f"Nominee name variation detected (similarity: {score:.0%})",
                    ev,
                    "name_variation_explanation",
                    "Verify the exact name spelling with the insurer and update the policy if needed.",
                )

        # 2. DOB comparison
        if linked_profile and nominee_dob:
            code = compare_dob(nominee_dob, linked_profile.get("date_of_birth"))
            if code:
                ev = [
                    EvidenceItem("DOB on policy (OCR/record)", str(nominee_dob), "POLICY_OCR"),
                    EvidenceItem("DOB on linked demo profile", str(linked_profile.get("date_of_birth")), "MOCK_LINKED_PROFILE"),
                ]
                sev = "REVIEW_REQUIRED" if code == "DOB_MISMATCH_REVIEW" else "ATTENTION"
                add_finding(
                    policy_id, code, sev,
                    "Date of birth mismatch or not available",
                    ev,
                    "dob_mismatch_explanation",
                    "Confirm the correct date of birth with the insurer.",
                )

        # 3. Relationship comparison
        if linked_profile and nominee_relationship:
            code = compare_relationship(nominee_relationship, linked_profile.get("relationship_to_policyholder"))
            if code:
                ev = [
                    EvidenceItem("Relationship on policy (OCR/record)", str(nominee_relationship), "POLICY_OCR"),
                    EvidenceItem("Relationship on linked demo profile", str(linked_profile.get("relationship_to_policyholder")), "MOCK_LINKED_PROFILE"),
                ]
                add_finding(
                    policy_id, code, "REVIEW_REQUIRED",
                    "Relationship mismatch between policy record and linked profile",
                    ev,
                    "relationship_mismatch_explanation",
                    "Confirm the correct relationship with the insurer.",
                )

        # 4. Minor nominee and appointee check
        code = check_minor_nominee(
            nominee_dob,
            event_date,
            product_type,
            appointee_name,
            appointee_relationship,
        )
        if code:
            ev = []
            if nominee_dob:
                ev.append(EvidenceItem("Nominee DOB on policy", str(nominee_dob), "POLICY_OCR"))
            if event_date:
                ev.append(EvidenceItem("Event date", str(event_date), "FAMILY_CASE"))
            if appointee_name:
                ev.append(EvidenceItem("Appointee name", str(appointee_name), "POLICY_OCR"))
            if appointee_relationship:
                ev.append(EvidenceItem("Appointee relationship", str(appointee_relationship), "POLICY_OCR"))
            sev = "REVIEW_REQUIRED" if code in {"MINOR_NOMINEE_APPOINTEE_REVIEW", "APPOINTEE_DETAILS_UNVERIFIED"} else "ATTENTION"
            add_finding(
                policy_id, code, sev,
                {
                    "MINOR_NOMINEE_APPOINTEE_REVIEW": "Nominee appears to be a minor at event date; appointee details not recorded",
                    "APPOINTEE_DETAILS_UNVERIFIED": "Appointee details present but insurer registration not confirmed",
                    "AGE_STATUS_UNKNOWN": "Cannot determine nominee age at event date",
                    "PRODUCT_RULE_CONFIRMATION_REQUIRED": "Minor/appointee rule requires product-specific insurer confirmation",
                }[code],
                ev,
                {
                    "MINOR_NOMINEE_APPOINTEE_REVIEW": "minor_nominee_life_policy_appointee_review",
                    "APPOINTEE_DETAILS_UNVERIFIED": "appointee_details_unverified_explanation",
                    "AGE_STATUS_UNKNOWN": "age_status_unknown_explanation",
                    "PRODUCT_RULE_CONFIRMATION_REQUIRED": "product_rule_confirmation_required_explanation",
                }[code],
                "Check the insurer's appointee/guardian requirements for this policy.",
            )

        # 5. Allocation check
        if nominee_share is not None:
            # For now just check if this single nominee has 100% share
            try:
                share_val = float(nominee_share)
                if abs(share_val - 100.0) > 0.01:
                    add_finding(
                        policy_id, "NOMINEE_SHARE_TOTAL_REVIEW", "ATTENTION",
                        f"Nominee share is {share_val}%, not 100%",
                        [EvidenceItem("Nominee share on policy", f"{share_val}%", "POLICY_OCR")],
                        "nominee_share_total_explanation",
                        "Confirm the nominee share allocation with the insurer.",
                    )
            except (TypeError, ValueError):
                pass

        # 6. Insurer registration status
        code = check_insurer_registration_status(policy)
        if code:
            add_finding(
                policy_id, code, "ATTENTION",
                "Insurer nomination registration not confirmed",
                [EvidenceItem("Registration status", str(policy.get("verification_status")), "POLICY_OCR")],
                "insurer_registration_not_confirmed_explanation",
                "Contact the insurer to confirm the nominee registration status.",
            )

        # 7. Nomination not found in uploaded document
        if policy.get("source_type") == "EXTERNAL_DOCUMENT":
            if not nominee_name and not nominee_dob and not nominee_relationship:
                add_finding(
                    policy_id, "NOMINATION_NOT_FOUND_IN_UPLOADED_DOCUMENT", "INFO",
                    "No nominee details found in the uploaded document",
                    [EvidenceItem("Document source", "Uploaded policy schedule", "POLICY_OCR")],
                    "nomination_not_found_explanation",
                    "This does not prove no nominee exists. Check with the insurer for the registered nomination.",
                )

    # 8. Cross-policy different nominees check
    nominee_names_by_policy = {}
    for policy in user_policies:
        name = policy.get("ocr_nominee_name") or policy.get("policyholder_name")
        if name:
            nominee_names_by_policy[policy["policy_id"]] = normalise_name_for_comparison(name)

    unique_nominees = set(nominee_names_by_policy.values())
    if len(unique_nominees) > 1:
        # Check if these are intentionally different (different people) vs variations
        for pid, nname in nominee_names_by_policy.items():
            # Only flag if not already captured by name variation finding
            has_variation = any(f.policy_id == pid and f.finding_code in {"NAME_VARIATION_REVIEW", "POSSIBLE_NAME_MISMATCH"} for f in findings)
            if not has_variation:
                ev = [EvidenceItem("Nominee on this policy", str(policy.get("ocr_nominee_name") or policy.get("policyholder_name")), "POLICY_OCR")
                      for p in user_policies if p["policy_id"] == pid]
                # Add other nominees as context
                other_names = [str(p.get("ocr_nominee_name") or p.get("policyholder_name"))
                               for p in user_policies if p["policy_id"] != pid and (p.get("ocr_nominee_name") or p.get("policyholder_name"))]
                if other_names:
                    ev.append(EvidenceItem("Nominees on other policies", "; ".join(other_names), "POLICY_OCR"))
                add_finding(
                    pid, "DIFFERENT_NOMINEES_ACROSS_POLICIES", "INFO",
                    "Different nominee name on this policy compared to other policies in the portfolio",
                    ev,
                    "different_nominees_explanation",
                    "Different nominees across policies can be intentional. Verify with the insurer if this is expected.",
                )

    # Portfolio summary
    summary = {
        "total_policies": len(user_policies),
        "policies_with_nominee_details": sum(1 for p in user_policies if p.get("ocr_nominee_name") or p.get("ocr_nominee_dob") or p.get("ocr_nominee_relationship")),
        "policies_with_unconfirmed_registration": sum(1 for p in user_policies if p.get("verification_status") in {"SIMULATED_NOT_VERIFIED", "OCR_EXTRACTED_NEEDS_REVIEW", "USER_REVIEWED_UNVERIFIED"}),
        "total_findings": len(findings),
        "findings_by_severity": {
            "INFO": sum(1 for f in findings if f.severity == "INFO"),
            "ATTENTION": sum(1 for f in findings if f.severity == "ATTENTION"),
            "REVIEW_REQUIRED": sum(1 for f in findings if f.severity == "REVIEW_REQUIRED"),
        },
        "analysis_version": "nominee-check-v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    return findings, summary


def load_linked_profiles() -> list[dict[str, Any]]:
    """Load mock linked profiles from JSON fixture."""
    from pathlib import Path
    import json
    path = Path(__file__).resolve().parent.parent / "data" / "mock_linked_profiles.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("profiles", [])


def get_consented_profile_fields(profile: Mapping[str, Any]) -> list[str]:
    """Return the list of consented fields for a profile."""
    return list(profile.get("consented_fields", []))


def is_profile_accessible(profile: Mapping[str, Any], required_fields: list[str] | None = None) -> bool:
    """Check if a linked profile can be accessed (accepted link + sharing consent)."""
    if str(profile.get("family_link_status")) != "ACCEPTED":
        return False
    if not profile.get("profile_sharing_consent"):
        return False
    if required_fields:
        consented = set(profile.get("consented_fields", []))
        if not all(f in consented for f in required_fields):
            return False
    return True


__all__ = [
    "Finding",
    "EvidenceItem",
    "FindingCode",
    "Severity",
    "analyse_portfolio",
    "load_linked_profiles",
    "get_consented_profile_fields",
    "is_profile_accessible",
    "normalise_name_for_comparison",
    "name_similarity",
    "parse_dob",
    "calculate_age",
    "compare_nominee_name",
    "compare_dob",
    "compare_relationship",
    "check_minor_nominee",
    "check_allocation_total",
    "check_insurer_registration_status",
]