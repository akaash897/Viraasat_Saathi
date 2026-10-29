"""Rule-based transaction clue matching.

The keyword dictionary is deliberately small and explicit. Every lead keeps
the exact source rows that caused the match, and recurrence requires matching
transactions in at least two *distinct calendar months*. A single row is never
labelled as a recurring pattern.

Nothing here infers a balance, coverage amount, units held, outstanding loan
principal, beneficiary, ownership or claim eligibility.
"""

from __future__ import annotations

import re
import unicodedata

from src.models import EvidenceRow, Lead, PatternStrength, TransactionRow
from src.translations import t

# (keyword, specificity weight). Weight 3 means a fairly specific phrase;
# weight 2 is broader. The weight only selects a transparent label, never a
# probability of ownership.
CATEGORY_KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "possible_insurance_payment": (
        ("LIFE PREMIUM", 3),
        ("HEALTH PREMIUM", 3),
        ("POLICY PREMIUM", 3),
        ("INSURANCE PREMIUM", 3),
        ("INSURANCE", 2),
        ("TERM PLAN", 2),
    ),
    "possible_investment_or_sip": (
        ("SYSTEMATIC INVESTMENT", 3),
        ("STAR MF SIP", 3),
        ("MUTUAL FUND", 3),
        ("SIP", 3),
        ("ELSS", 2),
        ("INVESTMENT", 2),
    ),
    "possible_lender_or_emi": (
        ("VEHICLE FINANCE EMI", 3),
        ("HOME FINANCE EMI", 3),
        ("PERSONAL LOAN EMI", 3),
        ("LOAN EMI", 3),
        ("EMI", 2),
        ("LOAN", 2),
    ),
    "possible_recurring_subscription": (
        ("STREAMING SUBSCRIPTION", 2),
        ("SUBSCRIPTION", 2),
        ("MONTHLY PLAN", 2),
        ("ANNUAL PLAN", 2),
        ("STREAMING", 2),
    ),
}

CATEGORY_ORDER = tuple(CATEGORY_KEYWORDS.keys())

CATEGORY_TRANSLATION_KEYS = {
    "possible_insurance_payment": "category_insurance",
    "possible_investment_or_sip": "category_investment",
    "possible_lender_or_emi": "category_lender",
    "possible_recurring_subscription": "category_subscription",
}

CATEGORY_SOURCE_IDS = {
    "possible_insurance_payment": ["bima_bharosa_faq", "irdai_health_dept"],
    "possible_investment_or_sip": [
        "common_landing_portal",
        "rbi_udgam",
        "iepfa",
        "sebi_investor_education",
    ],
    "possible_lender_or_emi": [],
    "possible_recurring_subscription": [],
}

CATEGORY_COPY_KEYS = {
    "possible_insurance_payment": ("does_not_prove_insurance", "next_step_insurance"),
    "possible_investment_or_sip": ("does_not_prove_investment", "next_step_investment"),
    "possible_lender_or_emi": ("does_not_prove_lender", "next_step_lender"),
    "possible_recurring_subscription": (
        "does_not_prove_subscription",
        "next_step_subscription",
    ),
}


def normalize_description(value: str) -> str:
    """Uppercase, strip punctuation/whitespace and collapse spaces.

    The normalizer does not extract, reconstruct or recover identifiers.
    """
    normalized = unicodedata.normalize("NFKC", value).upper()
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _best_keyword(normalized: str) -> tuple[str, int] | None:
    padded = f" {normalized} "
    best: tuple[str, int] | None = None
    for keyword, weight in (
        (keyword, weight)
        for keywords in CATEGORY_KEYWORDS.values()
        for keyword, weight in keywords
    ):
        if f" {keyword} " in padded:
            if best is None or weight > best[1]:
                best = (keyword, weight)
    return best


def _keyword_for_category(normalized: str, category_id: str) -> tuple[str, int] | None:
    padded = f" {normalized} "
    best: tuple[str, int] | None = None
    for keyword, weight in CATEGORY_KEYWORDS[category_id]:
        if f" {keyword} " in padded:
            if best is None or weight > best[1]:
                best = (keyword, weight)
    return best


def _strength(is_recurring: bool, specificity: int) -> PatternStrength:
    if not is_recurring:
        return "low"
    return "strong_pattern" if specificity >= 3 else "medium"


def _months_label(rows: list[TransactionRow]) -> str:
    months = sorted({(row.date.year, row.date.month) for row in rows})
    return ", ".join(f"{year}-{month:02d}" for year, month in months)


def match_transactions(rows: list[TransactionRow]) -> list[Lead]:
    """Return transparent leads, each with its exact supporting rows."""
    grouped: dict[str, dict[str, list[tuple[TransactionRow, str, int]]]] = {
        category_id: {} for category_id in CATEGORY_ORDER
    }

    for row in sorted(rows, key=lambda item: item.row_number):
        normalized = normalize_description(row.description)
        if not normalized:
            continue
        for category_id in CATEGORY_ORDER:
            match = _keyword_for_category(normalized, category_id)
            if match is None:
                continue
            keyword, specificity = match
            grouped[category_id].setdefault(normalized, []).append(
                (row, keyword, specificity)
            )

    leads: list[Lead] = []
    for category_id in CATEGORY_ORDER:
        for merchant_key, matches in grouped[category_id].items():
            matches.sort(key=lambda item: (item[0].date, item[0].row_number))
            source_rows = [item[0] for item in matches]
            keyword, specificity = max(matches, key=lambda item: item[2])[1:]
            distinct_months = len(
                {(row.date.year, row.date.month) for row in source_rows}
            )
            is_recurring = len(source_rows) >= 2 and distinct_months >= 2

            if len(source_rows) == 1:
                rule_key = "single_clue"
            elif is_recurring:
                rule_key = "recurring_pattern"
            else:
                rule_key = "same_month_multiple"

            months = _months_label(source_rows)
            rule_format = {
                "single_clue": t("rule_single", "en"),
                "same_month_multiple": t("rule_same_month", "en"),
                "recurring_pattern": t("rule_recurring", "en"),
            }[rule_key]
            rule_hi_format = {
                "single_clue": t("rule_single", "hi"),
                "same_month_multiple": t("rule_same_month", "hi"),
                "recurring_pattern": t("rule_recurring", "hi"),
            }[rule_key]
            format_values = {
                "keyword": keyword,
                "count": len(source_rows),
                "months": months,
                "month_count": distinct_months,
            }
            does_not_prove_key, next_step_key = CATEGORY_COPY_KEYS[category_id]

            leads.append(
                Lead(
                    lead_id=f"{category_id}-row-{source_rows[0].row_number}",
                    category_id=category_id,  # type: ignore[arg-type]
                    merchant_key=merchant_key,
                    pattern_strength=_strength(is_recurring, specificity),
                    is_recurring=is_recurring,
                    distinct_months=distinct_months,
                    matched_keyword=keyword,
                    evidence=[
                        EvidenceRow(
                            row_number=row.row_number,
                            date=row.date,
                            description=row.description,
                            amount=row.amount,
                            direction=row.direction,
                        )
                        for row in source_rows
                    ],
                    rule_key=rule_key,  # type: ignore[arg-type]
                    rule_en=rule_format.format(**format_values),
                    rule_hi=rule_hi_format.format(**format_values),
                    does_not_prove_en=t(does_not_prove_key, "en"),
                    does_not_prove_hi=t(does_not_prove_key, "hi"),
                    next_step_en=t(next_step_key, "en"),
                    next_step_hi=t(next_step_key, "hi"),
                    source_ids=CATEGORY_SOURCE_IDS[category_id],
                )
            )

    return leads


def category_label(category_id: str, language: str = "en") -> str:
    key = CATEGORY_TRANSLATION_KEYS.get(category_id)
    return t(key, language) if key else category_id  # type: ignore[arg-type]
