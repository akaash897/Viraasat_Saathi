from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.document_parser import UploadError, parse_transactions_csv
from src.fixtures import load_demo_transactions_bytes
from src.models import TransactionRow
from src.transaction_matcher import match_transactions, normalize_description


def demo_rows() -> list[TransactionRow]:
    return parse_transactions_csv(load_demo_transactions_bytes())


def test_demo_statement_produces_four_lead_categories() -> None:
    leads = match_transactions(demo_rows())
    assert len(leads) == 4
    assert {lead.category_id for lead in leads} == {
        "possible_insurance_payment",
        "possible_investment_or_sip",
        "possible_lender_or_emi",
        "possible_recurring_subscription",
    }
    assert all(lead.is_recurring for lead in leads)
    assert all(lead.distinct_months == 2 for lead in leads)


def test_matching_evidence_rows() -> None:
    rows = demo_rows()
    by_row = {row.row_number: row for row in rows}
    leads = match_transactions(rows)
    for lead in leads:
        assert lead.evidence
        for evidence in lead.evidence:
            source = by_row[evidence.row_number]
            assert evidence.date == source.date
            assert evidence.description == source.description
            assert evidence.amount == source.amount
            assert evidence.direction == source.direction


def test_single_transaction_low_confidence() -> None:
    row = TransactionRow(
        row_number=2,
        date=date(2026, 1, 5),
        description="DEMO ABC LIFE PREMIUM",
        amount=Decimal("1850"),
        direction="debit",
    )
    leads = match_transactions([row])
    assert len(leads) == 1
    lead = leads[0]
    assert lead.is_recurring is False
    assert lead.pattern_strength == "low"
    assert lead.rule_key == "single_clue"
    assert lead.distinct_months == 1
    assert "single clue" in lead.rule_en.lower()
    assert "recurring pattern" in lead.rule_en.lower()


def test_recurrence_needs_distinct_months() -> None:
    rows = [
        TransactionRow(
            row_number=2,
            date=date(2026, 1, 5),
            description="DEMO ABC LIFE PREMIUM",
            amount=Decimal("1850"),
            direction="debit",
        ),
        TransactionRow(
            row_number=3,
            date=date(2026, 1, 25),
            description="DEMO ABC LIFE PREMIUM",
            amount=Decimal("1850"),
            direction="debit",
        ),
    ]
    leads = match_transactions(rows)
    assert len(leads) == 1
    lead = leads[0]
    assert lead.is_recurring is False
    assert lead.pattern_strength == "low"
    assert lead.rule_key == "same_month_multiple"
    assert lead.distinct_months == 1
    assert "does not establish monthly recurrence" in lead.rule_en


def test_distinct_months_satisfy_recurrence() -> None:
    rows = [
        TransactionRow(
            row_number=2,
            date=date(2026, 1, 5),
            description="DEMO ABC LIFE PREMIUM",
            amount=Decimal("1850"),
            direction="debit",
        ),
        TransactionRow(
            row_number=3,
            date=date(2026, 2, 5),
            description="DEMO ABC LIFE PREMIUM",
            amount=Decimal("1850"),
            direction="debit",
        ),
    ]
    leads = match_transactions(rows)
    assert len(leads) == 1
    lead = leads[0]
    assert lead.is_recurring is True
    assert lead.distinct_months == 2
    assert lead.pattern_strength == "strong_pattern"
    assert lead.rule_key == "recurring_pattern"


def test_normalization_is_punctuation_and_case_insensitive() -> None:
    assert normalize_description("  demo—abc   life premium!! ") == "DEMO ABC LIFE PREMIUM"
    assert normalize_description("DEMO.ABC/LIFE-PREMIUM") == "DEMO ABC LIFE PREMIUM"


def test_keyword_matching_is_token_aware() -> None:
    row = TransactionRow(
        row_number=2,
        date=date(2026, 1, 5),
        description="DEMO PARTICIPATION FEE",
        amount=Decimal("10"),
        direction="debit",
    )
    assert match_transactions([row]) == []


def test_every_lead_is_caveated() -> None:
    for lead in match_transactions(demo_rows()):
        assert lead.does_not_prove_en
        assert lead.does_not_prove_hi
        assert lead.next_step_en
        assert lead.next_step_hi
        assert "does not prove" in lead.does_not_prove_en.lower()
        assert "lead" not in lead.rule_en.lower() or "not proof" in lead.rule_en.lower()


def test_malformed_csv_is_rejected() -> None:
    with pytest.raises(UploadError):
        parse_transactions_csv(b"date,description,amount\n2026-01-01,DEMO,10\n")
    with pytest.raises(UploadError):
        parse_transactions_csv(b"date,description,amount,direction\nnot-a-date,DEMO,10,debit\n")
    with pytest.raises(UploadError):
        parse_transactions_csv(b"date,description,amount,direction\n2026-01-01,DEMO,-10,debit\n")
    with pytest.raises(UploadError):
        parse_transactions_csv(b"date,description,amount,direction\n2026-01-01,DEMO,10,sideways\n")
    with pytest.raises(UploadError):
        parse_transactions_csv(b"")
