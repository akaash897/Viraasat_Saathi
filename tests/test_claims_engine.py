from __future__ import annotations

from src.claims_engine import (
    answer_policy_topic,
    case_summary_text,
    checklist_progress,
    checklist_status,
    validate_claim_against_policy,
)
from src.fixtures import load_claim, load_policy


def test_fixtures_are_fictional_and_citations_valid() -> None:
    claim = load_claim()
    policy = load_policy()
    assert claim.fictional_notice is True
    assert policy.fictional_notice is True
    assert validate_claim_against_policy(claim, policy) == []


def test_required_document_count() -> None:
    claim = load_claim()
    total = len(claim.required_document_categories)
    assert total == 7

    progress = checklist_progress(claim, set())
    assert progress.total == total
    assert progress.marked == 0
    assert progress.remaining == total

    first = claim.required_document_categories[0].id
    second = claim.required_document_categories[1].id
    progress = checklist_progress(claim, {first})
    assert progress.marked == 1
    assert progress.remaining == total - 1

    progress = checklist_progress(claim, {first, second})
    assert progress.marked == 2
    assert progress.remaining == total - 2

    progress = checklist_progress(claim, {first})
    assert progress.remaining == total - 1

    all_ids = {item.id for item in claim.required_document_categories}
    progress = checklist_progress(claim, all_ids)
    assert progress.marked == total
    assert progress.remaining == 0
    assert progress.insurer_validated is False


def test_unknown_checklist_ids_are_ignored() -> None:
    claim = load_claim()
    progress = checklist_progress(claim, {"not_a_category"})
    assert progress.marked == 0
    assert progress.remaining == progress.total


def test_checklist_status_wording_is_neutral() -> None:
    claim = load_claim()
    conditional = next(
        item for item in claim.required_document_categories if item.needs_confirmation
    )
    normal = next(
        item for item in claim.required_document_categories if not item.needs_confirmation
    )
    assert checklist_status(normal, set()) == "not_marked"
    assert checklist_status(normal, {normal.id}) == "marked_provided"
    assert checklist_status(conditional, set()) == "needs_confirmation"
    assert checklist_status(conditional, {conditional.id}) == "marked_provided"


def test_policy_clause_citations() -> None:
    policy = load_policy()
    clause_ids = {clause.id for clause in policy.clauses}
    assert policy.facts
    for fact in policy.facts:
        assert fact.clause_id in clause_ids
        answer = answer_policy_topic(policy, fact.topic)
        assert answer.verified is True
        assert answer.clause_id == fact.clause_id
        assert answer.page == fact.page
        assert answer.source_label
        clause = policy.clause_by_id(answer.clause_id)
        assert clause is not None
        assert clause.page == answer.page


def test_unknown_policy_topic_is_not_verified() -> None:
    policy = load_policy()
    answer = answer_policy_topic(policy, "is_my_claim_approved")
    assert answer.verified is False
    assert answer.clause_id is None
    assert answer.page is None
    assert "Not verified" in answer.statement_en
    assert "सत्यापित नहीं" in answer.statement_hi


def test_case_summary_has_demo_watermark_and_no_approval_claim() -> None:
    claim = load_claim()
    policy = load_policy()
    summary = case_summary_text(
        claim,
        policy,
        {claim.required_document_categories[0].id},
        {
            claim.timeline[0].id: {
                "done": True,
                "due": "2026-11-01",
                "notes": "Demo note",
            }
        },
        "en",
    )
    assert "DEMO" in summary
    assert claim.case_id in summary
    assert "not insurer validation" in summary.lower()
    assert "approved" not in summary.lower()
    assert "guaranteed" not in summary.lower()

    hindi = case_summary_text(claim, policy, set(), {}, "hi")
    assert "डेमो" in hindi
    assert claim.case_id in hindi
