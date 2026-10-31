"""UI components for Nominee 360 (Cross-Policy Nominee Consistency Intelligence)."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from src.insurance_inventory import (
    NOT_FOUND,
    seeded_paytm_records,
    display_date,
    display_value,
    source_label,
    verification_label,
)
from src.mock_auth import login_id_for_user
from src.mock_paytm_data import demo_user_by_id, users_as_dicts
from src.nominee_consistency import (
    Finding,
    EvidenceItem,
    FindingCode,
    Severity,
    analyse_portfolio,
    load_linked_profiles,
    is_profile_accessible,
    get_consented_profile_fields,
)
from src.nominee_demo import active_nominee_link_for_policy

NOMINEE_360_NOTICE = (
    "Virasat Saathi will compare nominee details visible in your saved policy records "
    "with information shared by family members through the simulated Paytm link. "
    "This is a data-consistency check, not proof of identity, legal eligibility or insurer registration. "
    "You can review every finding before taking action."
)

SEVERITY_COLORS = {
    "INFO": "#0B5C55",
    "ATTENTION": "#7A5200",
    "REVIEW_REQUIRED": "#A62C2C",
}
SEVERITY_BG = {
    "INFO": "#E6F3F1",
    "ATTENTION": "#FFF1D6",
    "REVIEW_REQUIRED": "#FDECEC",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pill(text: str, css_class: str = "vs-pill-neutral") -> str:
    return f'<span class="vs-pill {css_class}">{esc(text)}</span>'


def _render_evidence(evidence: Sequence[EvidenceItem]) -> None:
    if not evidence:
        return
    for item in evidence:
        st.markdown(
            f'<div class="vs-evidence"><strong>{esc(item.label)}:</strong> {esc(item.value)} '
            f'<span class="vs-mono">[{esc(item.source)}]</span></div>',
            unsafe_allow_html=True,
        )


def _render_finding(finding: Finding) -> None:
    sev = finding.severity
    border_color = SEVERITY_COLORS.get(sev, "#7A5200")
    bg_color = SEVERITY_BG.get(sev, "#FFF1D6")

    st.markdown(
        f"""
        <div style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 12px 16px; border-radius: 8px; margin: 10px 0;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong>{esc(finding.summary)}</strong>
            <span>{pill(sev, 'vs-pill-review')}</span>
          </div>
          <div class="vs-mono" style="margin-top: 4px;">Finding: {esc(finding.finding_code)} · Policy: {esc(finding.policy_id)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_evidence(finding.evidence)

    st.caption(f"Recommended action: {finding.recommended_user_action}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(
            "Reviewed — no change",
            key=f"vs_nom360_reviewed_{finding.finding_id}",
            width="stretch",
        ):
            st.session_state[f"vs_nom360_finding_status_{finding.finding_id}"] = "REVIEWED"
            st.rerun()
    with col2:
        if st.button(
            "Correct demo data",
            key=f"vs_nom360_correct_{finding.finding_id}",
            width="stretch",
        ):
            st.session_state[f"vs_nom360_finding_status_{finding.finding_id}"] = "CORRECTED"
            st.rerun()
    with col3:
        if st.button(
            "Intentionally different",
            key=f"vs_nom360_intentional_{finding.finding_id}",
            width="stretch",
        ):
            st.session_state[f"vs_nom360_finding_status_{finding.finding_id}"] = "INTENTIONAL"
            st.rerun()
    with col4:
        if st.button(
            "Ask insurer / unresolved",
            key=f"vs_nom360_ask_{finding.finding_id}",
            width="stretch",
        ):
            st.session_state[f"vs_nom360_finding_status_{finding.finding_id}"] = "ASK_INSURER"
            st.rerun()

    status = st.session_state.get(f"vs_nom360_finding_status_{finding.finding_id}", "OPEN")
    st.caption(f"Current status: {status}")

    st.divider()


def _render_linked_profiles(linked_profiles: Sequence[Mapping[str, Any]]) -> None:
    st.markdown("#### Linked demo family profiles")
    st.caption(
        "Only profiles with accepted links and field-level consent are available for comparison."
    )
    for profile in linked_profiles:
        accessible = is_profile_accessible(profile)
        consented = get_consented_profile_fields(profile)
        with st.container(border=True):
            st.markdown(f"**{esc(profile.get('display_name', 'Unknown'))}**")
            st.caption(f"@ {esc(profile.get('demo_paytm_user_id', ''))}")
            st.caption(f"Link status: {esc(str(profile.get('family_link_status', '')))}")
            if accessible:
                st.success("Profile accessible for comparison")
                cols = st.columns(2)
                with cols[0]:
                    st.write(f"Legal name: {esc(profile.get('legal_name_demo', ''))}")
                    st.write(f"DOB: {esc(profile.get('date_of_birth', ''))}")
                with cols[1]:
                    st.write(f"Relationship: {esc(profile.get('relationship_to_policyholder', ''))}")
                    st.write(f"Age band: {esc(profile.get('age_band', ''))}")
                st.caption(f"Consented fields: {', '.join(consented)}")
            else:
                st.warning("Profile details not shared (consent not granted or link not accepted)")
                st.caption("Profile details not shared — consent required for comparison")
        st.write("")


def _render_portfolio_summary(summary: dict[str, Any]) -> None:
    st.markdown("#### Portfolio summary")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Policies analysed", summary.get("total_policies", 0))
    with cols[1]:
        st.metric("With nominee details", summary.get("policies_with_nominee_details", 0))
    with cols[2]:
        st.metric("Unconfirmed registration", summary.get("policies_with_unconfirmed_registration", 0))
    with cols[3]:
        st.metric("Review flags", summary.get("total_findings", 0))

    sev = summary.get("findings_by_severity", {})
    if sev:
        st.write("")
        sev_cols = st.columns(3)
        with sev_cols[0]:
            st.metric("INFO", sev.get("INFO", 0))
        with sev_cols[1]:
            st.metric("ATTENTION", sev.get("ATTENTION", 0))
        with sev_cols[2]:
            st.metric("REVIEW_REQUIRED", sev.get("REVIEW_REQUIRED", 0))


def _render_policy_comparison(
    findings: list[Finding],
    owner_demo_user_id: str,
    event_date: date | None,
) -> None:
    st.markdown("#### Per-policy nominee comparison")

    policies = seeded_paytm_records()
    user_policies = [p for p in policies if p.get("owner_demo_user_id") == owner_demo_user_id]

    for policy in user_policies:
        policy_id = str(policy.get("policy_id", ""))
        policy_findings = [f for f in findings if f.policy_id == policy_id]

        with st.container(border=True):
            st.markdown(f"**{esc(display_value(policy.get('product_name')))}**")
            st.caption(f"{esc(source_label(policy.get('source_type')))} · {esc(verification_label(policy.get('verification_status')))}")
            st.caption(f"Masked policy ID: {esc(policy.get('policy_number_masked', NOT_FOUND))}")

            # Nominee details from policy
            nominee_name = policy.get("ocr_nominee_name") or policy.get("policyholder_name")
            nominee_dob = policy.get("ocr_nominee_dob")
            nominee_rel = policy.get("ocr_nominee_relationship")

            cols = st.columns(2)
            with cols[0]:
                st.write(f"Nominee name: {esc(display_value(nominee_name))}")
                st.write(f"DOB: {esc(display_value(nominee_dob))}")
            with cols[1]:
                st.write(f"Relationship: {esc(display_value(nominee_rel))}")
                st.write(f"Registration: {esc(policy.get('verification_status', NOT_FOUND))}")

            # Linked profile info if available
            # This would be populated via the analysis

            if policy_findings:
                st.write("**Findings:**")
                for f in policy_findings:
                    _render_finding(f)
            else:
                st.info("No review flags for this policy")


def _render_sarvam_explanation(findings: list[Finding]) -> None:
    st.markdown("#### AI explanation (Sarvam-105B)")
    st.caption(
        "The explanation below is generated by Sarvam-105B from the deterministic findings. "
        "It does not decide legal eligibility, approve claims, or change any records. "
        "Click the button to generate an explanation. If Sarvam is unavailable, a deterministic fallback is shown."
    )

    # Check if Sarvam is configured
    from src.sarvam_service import SarvamConfig, SarvamService
    config = SarvamConfig.from_env()

    if not config.is_configured:
        st.info("Sarvam-105B not configured. Showing deterministic explanation templates.")
        _render_deterministic_explanation(findings)
        return

    # Button to trigger AI explanation
    if st.button("Generate AI explanation", key="vs_nom360_ai_explain", type="primary", width="stretch"):
        service = SarvamService(config)
        # Prepare findings for the LLM (redacted)
        findings_for_llm = []
        for f in findings:
            findings_for_llm.append({
                "finding_id": f.finding_id,
                "policy_id": f.policy_id,
                "finding_code": f.finding_code,
                "severity": f.severity,
                "summary": f.summary,
                "evidence": [{"label": e.label, "value": e.value, "source": e.source} for e in f.evidence],
                "explanation_key": f.explanation_key,
            })
        language_name = "English"  # UI is English-only
        try:
            result = service.explain_nominee_findings("en", findings_for_llm, language_name)
            st.session_state["vs_nom360_ai_result"] = result.text
            st.session_state["vs_nom360_ai_status"] = result.status
            st.session_state["vs_nom360_ai_elapsed"] = result.elapsed_ms
        except Exception as e:
            st.session_state["vs_nom360_ai_error"] = str(e)

    # Display result if available
    if "vs_nom360_ai_result" in st.session_state:
        status = st.session_state.get("vs_nom360_ai_status", "unknown")
        elapsed = st.session_state.get("vs_nom360_ai_elapsed", 0)
        if status == "success":
            st.success(f"AI explanation generated ({elapsed} ms)")
        elif status == "fallback":
            st.warning(f"AI unavailable, showing fallback ({elapsed} ms)")
        else:
            st.info(f"Status: {status}")

        try:
            ai_data = json.loads(st.session_state["vs_nom360_ai_result"])
            st.markdown(f"**Portfolio summary:** {ai_data.get('portfolio_summary', '')}")
            for exp in ai_data.get("finding_explanations", []):
                with st.expander(f"Finding: {exp.get('finding_id', '')}"):
                    st.write(f"**Explanation:** {exp.get('plain_language_explanation', '')}")
                    st.write(f"**What to verify:** {exp.get('what_to_verify', '')}")
                    st.caption(f"Sources: {', '.join(exp.get('source_ids', []))}")
            st.markdown(f"**Portfolio note:** {ai_data.get('portfolio_note', '')}")
        except json.JSONDecodeError:
            st.error("Failed to parse AI response")
            st.code(st.session_state["vs_nom360_ai_result"])

    if "vs_nom360_ai_error" in st.session_state:
        st.error(f"AI error: {st.session_state['vs_nom360_ai_error']}")
        _render_deterministic_explanation(findings)
    elif "vs_nom360_ai_result" not in st.session_state:
        st.info("Click the button above to generate an AI explanation.")
        _render_deterministic_explanation(findings)


def _render_deterministic_explanation(findings: list[Finding]) -> None:
    """Render deterministic fallback explanations grouped by finding code."""
    explanations = {
        "NAME_VARIATION_REVIEW": (
            "The nominee name on the policy differs slightly from the linked profile (e.g., initial vs full name). "
            "This is often a data-entry variation. Verify the exact spelling with the insurer."
        ),
        "POSSIBLE_NAME_MISMATCH": (
            "The nominee name on the policy may not match the linked profile. "
            "This could be a different person or a significant spelling difference. Confirm with the insurer."
        ),
        "DOB_MISMATCH_REVIEW": (
            "The date of birth on the policy differs from the linked profile. "
            "This affects age calculations and minor/appointee checks. Confirm the correct DOB with the insurer."
        ),
        "DOB_NOT_AVAILABLE": (
            "Date of birth is missing from either the policy record or the linked profile. "
            "Age-based checks (minor/appointee) cannot be completed without it."
        ),
        "RELATIONSHIP_MISMATCH_REVIEW": (
            "The relationship stated on the policy differs from the linked family profile. "
            "This could be a data-entry error or an intentional difference. Confirm with the insurer."
        ),
        "MINOR_NOMINEE_APPOINTEE_REVIEW": (
            "The nominee appears to be under 18 at the event date on a life policy, "
            "and no appointee/guardian is recorded in the available source. "
            "Per Section 39(1) of the Insurance Act, 1938, a minor nominee is permitted "
            "but the policyholder must appoint a person to receive the money during minority. "
            "Check the insurer's prescribed process and required appointee details."
        ),
        "APPOINTEE_DETAILS_UNVERIFIED": (
            "Appointee/guardian details are present in the policy record but insurer registration "
            "is not confirmed. Verify the appointee details with the insurer."
        ),
        "AGE_STATUS_UNKNOWN": (
            "Cannot determine nominee age at the event date because DOB or event date is missing. "
            "Provide the missing date to complete the check."
        ),
        "NOMINEE_SHARE_TOTAL_REVIEW": (
            "The nominee share percentage on the policy does not total 100%. "
            "Confirm the correct allocation with the insurer."
        ),
        "NOMINATION_NOT_FOUND_IN_UPLOADED_DOCUMENT": (
            "No nominee details were found in the uploaded document. "
            "This does not prove no nominee exists — the document may not contain the nomination page, "
            "or the OCR may have missed it. Check with the insurer for the registered nomination."
        ),
        "INSURER_REGISTRATION_NOT_CONFIRMED": (
            "The nominee registration status with the insurer is not confirmed. "
            "OCR extraction or user entry is not the same as insurer acknowledgement. "
            "Contact the insurer to verify the nomination status."
        ),
        "DIFFERENT_NOMINEES_ACROSS_POLICIES": (
            "Different nominees are named on different policies in this portfolio. "
            "This can be intentional (e.g., different nominees for different policies). "
            "It is not inherently an error. Verify with the insurer if this is expected."
        ),
        "PROFILE_DETAILS_NOT_SHARED": (
            "The linked family profile has not consented to share the required fields (DOB, legal name, relationship). "
            "Comparison for those fields cannot be performed."
        ),
        "PRODUCT_RULE_CONFIRMATION_REQUIRED": (
            "The minor/appointee rule applied here is specific to life insurance (Section 39, Insurance Act 1938). "
            "For general/health products, insurer/product-specific rules apply. Confirm with the insurer."
        ),
    }

    # Group findings by code
    from collections import defaultdict
    grouped = defaultdict(list)
    for f in findings:
        grouped[f.finding_code].append(f)

    for code, f_list in grouped.items():
        with st.expander(f"{code} ({len(f_list)} finding(s))"):
            st.write(explanations.get(code, "No deterministic explanation available."))
            st.caption("This is a deterministic template. Sarvam-105B would provide a contextual summary.")


def render_nominee_360(
    *,
    owner_demo_user_id: str,
    event_date: date | None = None,
) -> None:
    """Render the Nominee 360 analysis view."""
    from datetime import date as dt_date

    if event_date is None:
        event_date = dt_date.today()

    st.markdown("## Nominee 360 — Portfolio Nominee Consistency Check")
    st.info(NOMINEE_360_NOTICE)
    st.divider()

    # Load linked profiles
    linked_profiles = load_linked_profiles()

    # Show linked profiles and consent status
    _render_linked_profiles(linked_profiles)

    st.divider()

    # Run analysis button
    if st.button("Analyse my portfolio", key="vs_nom360_analyse", type="primary", width="stretch"):
        from src.insurance_ui import _active_user
        users = users_as_dicts()
        owner = _active_user(users)
        links = list(st.session_state.get("vs_insurance_links", []))
        findings, summary = analyse_portfolio(
            owner_demo_user_id=owner_demo_user_id,
            event_date=event_date,
            linked_profiles=linked_profiles,
            nominee_links=links,
        )
        st.session_state["vs_nom360_findings"] = [f.__dict__ for f in findings]
        st.session_state["vs_nom360_summary"] = summary
        st.session_state["vs_nom360_event_date"] = event_date.isoformat()
        st.rerun()

    # Display results if available
    if "vs_nom360_findings" in st.session_state:
        findings = [Finding(**f) for f in st.session_state["vs_nom360_findings"]]
        summary = st.session_state.get("vs_nom360_summary", {})
        event_date = dt_date.fromisoformat(st.session_state.get("vs_nom360_event_date", dt_date.today().isoformat()))

        _render_portfolio_summary(summary)
        st.divider()
        _render_policy_comparison(findings, owner_demo_user_id, event_date)
        st.divider()
        _render_sarvam_explanation(findings)

        # Download report
        report = {
            "analysis_type": "NOMINEE_360_DEMO",
            "generated_at": dt_date.today().isoformat(),
            "event_date": event_date.isoformat(),
            "owner_demo_user_id": owner_demo_user_id,
            "summary": summary,
            "findings": [f.__dict__ for f in findings],
            "disclaimer": "DEMO ANALYSIS — NOT AN INSURER OR LEGAL DETERMINATION",
        }
        st.download_button(
            "Download portfolio report (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name=f"nominee_360_report_{owner_demo_user_id}.json",
            mime="application/json",
            key="vs_nom360_download",
        )


__all__ = ["render_nominee_360"]