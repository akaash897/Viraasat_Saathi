"""Deterministic claims logic.

All decisions here are simple rules over the fictional fixtures. No model call
is involved, and no function decides coverage, eligibility or claim approval.
"""

from __future__ import annotations

from src.models import (
    ChecklistCategory,
    ChecklistProgress,
    ChecklistStatus,
    DemoClaim,
    DemoPolicy,
    Language,
    PolicyAnswer,
)


def checklist_status(category: ChecklistCategory, provided_ids: set[str]) -> ChecklistStatus:
    """Return a neutral status label; this is never insurer validation."""
    if category.id in provided_ids:
        return "marked_provided"
    if category.needs_confirmation:
        return "needs_confirmation"
    return "not_marked"


def checklist_progress(claim: DemoClaim, provided_ids: set[str]) -> ChecklistProgress:
    """Count checklist categories deterministically.

    ``remaining`` counts every category the user has not marked. Marking an
    item means only that the user marked it provided. It is not validation,
    authentication or a statement that the insurer will accept it.
    """
    known_ids = {item.id for item in claim.required_document_categories}
    marked = len(known_ids & set(provided_ids))
    needs_confirmation = sum(
        1
        for item in claim.required_document_categories
        if item.id not in provided_ids and item.needs_confirmation
    )
    total = len(known_ids)
    return ChecklistProgress(
        total=total,
        marked=marked,
        remaining=total - marked,
        needs_confirmation=needs_confirmation,
        insurer_validated=False,
    )


def answer_policy_topic(policy: DemoPolicy, topic: str) -> PolicyAnswer:
    """Answer only from the fictional policy fixture, with a clause citation."""
    fact = policy.fact_by_topic(topic)
    if fact is None:
        return PolicyAnswer(
            topic=topic,
            verified=False,
            statement_en=(
                "Not verified in the available information. This prototype only answers "
                "from the fictional demo policy fixture. Check the insurer's official "
                "policy wording for your question."
            ),
            statement_hi=(
                "उपलब्ध जानकारी में सत्यापित नहीं है। यह प्रोटोटाइप केवल काल्पनिक डेमो "
                "पॉलिसी फ़िक्सचर से उत्तर देता है। अपने प्रश्न के लिए बीमाकर्ता के "
                "आधिकारिक पॉलिसी पाठ की जाँच करें।"
            ),
            clause_id=None,
            page=None,
            source_label="Not verified in the available information",
        )
    return PolicyAnswer(
        topic=topic,
        verified=True,
        statement_en=fact.statement_en,
        statement_hi=fact.statement_hi,
        clause_id=fact.clause_id,
        page=fact.page,
        source_label=f"{fact.clause_id} · page {fact.page}",
    )


def validate_claim_against_policy(claim: DemoClaim, policy: DemoPolicy) -> list[str]:
    """Return human-readable fixture problems; an empty list means valid."""
    errors: list[str] = []
    if claim.checklist_source_id != "demo_checklist_01":
        errors.append("claim checklist source is not the fictional demo checklist")
    for category in claim.required_document_categories:
        if category.source_clause_id == "demo_checklist_01":
            continue
        clause = policy.clause_by_id(category.source_clause_id)
        if clause is None:
            errors.append(
                f"checklist category {category.id} cites unknown clause "
                f"{category.source_clause_id}"
            )
            continue
        if clause.page != category.source_page:
            errors.append(
                f"checklist category {category.id} page {category.source_page} "
                f"does not match clause page {clause.page}"
            )
    return errors


def case_summary_text(
    claim: DemoClaim,
    policy: DemoPolicy,
    provided_ids: set[str],
    tracker: dict[str, dict[str, object]],
    language: Language = "en",
) -> str:
    """Build an in-memory downloadable case summary with a DEMO watermark."""
    progress = checklist_progress(claim, provided_ids)
    if language == "hi":
        lines = [
            "डेमो — यह वास्तविक दावा नहीं है",
            "=" * 42,
            f"केस: {claim.case_id}",
            f"उत्पाद: स्वास्थ्य बीमा",
            f"दावा प्रकार: डिस्चार्ज के बाद प्रतिपूर्ति",
            f"दावे की स्थिति: {claim.claim_status_label_hi}",
            f"पॉलिसी: {policy.policy_name}",
            f"चेकलिस्ट स्रोत: {claim.checklist_source_id}",
            "",
            "दस्तावेज़ चेकलिस्ट (केवल उपयोगकर्ता की पहचान):",
        ]
        for item in claim.required_document_categories:
            mark = "x" if item.id in provided_ids else " "
            status = {
                "marked_provided": "उपयोगकर्ता ने प्रदान के रूप में चिह्नित किया",
                "needs_confirmation": "बीमाकर्ता से पुष्टि करनी है",
                "not_marked": "चिह्नित नहीं",
            }[checklist_status(item, provided_ids)]
            lines.append(f"[{mark}] {item.label_hi} — {status} ({item.source_clause_id})")
        lines.extend(
            [
                "",
                f"चिह्नित: {progress.marked} / {progress.total}; शेष: {progress.remaining}",
                "यह बीमाकर्ता द्वारा सत्यापन नहीं है और स्वीकृति का संकेत नहीं है।",
                "",
                "अगले कदम (सत्र-आधारित):",
            ]
        )
        for step in claim.timeline:
            state = tracker.get(step.id, {})
            done = "पूर्ण" if state.get("done") else "अपूर्ण"
            due = str(state.get("due") or "कोई तारीख दर्ज नहीं")
            notes = str(state.get("notes") or "")
            lines.append(f"- {step.stage_hi} — {done}; अनुस्मारक: {due}")
            if notes:
                lines.append(f"  नोट: {notes}")
        lines.extend(
            [
                "",
                "सुरक्षा: दावा छुड़ाने के लिए शुल्क न दें, अजनबी का QR स्कैन न करें,",
                "और OTP, UPI पिन, पासवर्ड या कार्ड पिन साझा न करें।",
                "यह सारांश एक प्रोटोटाइप द्वारा बनाया गया है। यह बीमाकर्ता का निर्णय,",
                "कानूनी सलाह या कवरेज का प्रमाण नहीं है।",
            ]
        )
        return "\n".join(lines)

    lines = [
        "DEMO — THIS IS NOT A REAL CLAIM",
        "=" * 42,
        f"Case: {claim.case_id}",
        "Product: health insurance",
        "Claim type: reimbursement after hospital discharge",
        f"Claim state: {claim.claim_status_label_en}",
        f"Policy: {policy.policy_name}",
        f"Checklist source: {claim.checklist_source_id}",
        "",
        "Document checklist (user markings only):",
    ]
    for item in claim.required_document_categories:
        mark = "x" if item.id in provided_ids else " "
        status = {
            "marked_provided": "marked provided by user",
            "needs_confirmation": "need to confirm with insurer",
            "not_marked": "not marked",
        }[checklist_status(item, provided_ids)]
        lines.append(f"[{mark}] {item.label_en} — {status} ({item.source_clause_id})")
    lines.extend(
        [
            "",
            f"Marked: {progress.marked} / {progress.total}; remaining: {progress.remaining}",
            "This is not insurer validation and does not imply acceptance.",
            "",
            "Next steps (session-only):",
        ]
    )
    for step in claim.timeline:
        state = tracker.get(step.id, {})
        done = "done" if state.get("done") else "not done"
        due = str(state.get("due") or "no reminder date entered")
        notes = str(state.get("notes") or "")
        lines.append(f"- {step.stage_en} — {done}; reminder: {due}")
        if notes:
            lines.append(f"  note: {notes}")
    lines.extend(
        [
            "",
            "Safety: never pay a fee to release a claim, never scan a QR code from a",
            "stranger, and never share an OTP, UPI PIN, password or card PIN.",
            "This summary was generated by a prototype. It is not an insurer decision,",
            "legal advice or proof of coverage.",
        ]
    )
    return "\n".join(lines)
