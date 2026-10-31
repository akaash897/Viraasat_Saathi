"""Paytm-style demo UI for the Phase 2 Active Insurances area.

This module is additive: it sits beside the Phase 1 Claims and Family journeys
and never calls Paytm. Sarvam Document AI is the only live external call.
"""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from src.insurance_inventory import (
    NOMINEE_LEGAL_WORDING,
    PRODUCT_TYPES,
    PROTOTYPE_LABEL,
    active_nominee_link_for_policy,
    all_policy_records,
    display_date,
    display_value,
    ensure_insurance_session,
    external_policies_for_user,
    find_policy,
    limited_shared_summary,
    nominee_invitations_for_user,
    nominee_status_label,
    owner_links_for_user,
    paytm_policies_for_user,
    remove_external_policy_session,
    reset_insurance_session,
    seeded_paytm_records,
    source_label,
    verification_label,
)
from src.mock_paytm_data import (
    demo_user_by_id,
    seeded_nominee_links_as_dicts,
    users_as_dicts,
)
from src.nominee_demo import (
    RELATIONSHIP_OPTIONS,
    NomineeError,
    can_manage_nominee,
    create_nominee_link,
    find_demo_user,
    link_created_message,
    relationship_label,
    replace_link,
    respond_to_nominee_link,
    revoke_nominee_link,
)
from src.policy_normalizer import (
    build_external_policy,
    external_record_is_reviewable,
    review_external_policy,
)
from src.sarvam_document_ai import (
    ALLOWED_DOCUMENT_LANGUAGES,
    DocumentAiConfig,
    DocumentAiError,
    SarvamDocumentAI,
)
from src.upload_validation import (
    UploadValidationError,
    validate_insurance_upload,
)

UPLOAD_DISCLOSURE = (
    "This document may contain personal, financial or health information. If "
    "you continue, the selected file will be transmitted to Sarvam AI Document "
    "AI for extraction. Do not upload a document unless you are authorised to "
    "share it. Review the provider's applicable data handling terms before "
    "using real customer documents."
)
PAYTM_SESSION_NOTE = (
    "Simulated session only. No login, OTP, UPI PIN, password or real Paytm "
    "credentials are collected, and no Paytm API is called."
)
SECTION_LABELS = {
    "bought": "Bought on Paytm",
    "external": "External Insurance",
    "nominee": "Nominee-linked Policies",
}
OCR_REVIEW_NOTE = (
    "OCR is fallible. Missing fields stay Not found in document. This is not "
    "insurer verification and does not prove the policy is in force."
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pill(text: str, css_class: str = "vs-pill-neutral") -> str:
    return f'<span class="vs-pill {css_class}">{esc(text)}</span>'


def warning_box(text: str) -> str:
    return f'<div class="vs-warning" role="note">{esc(text)}</div>'


def info_box(text: str) -> str:
    return f'<div class="vs-note">{esc(text)}</div>'


def _active_user(users: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    active_id = str(st.session_state.get("vs_insurance_active_user_id", ""))
    user = find_demo_user(users, active_id)
    if user is None:
        user = dict(users[0])
        st.session_state["vs_insurance_active_user_id"] = user["demo_user_id"]
    return user


def _user_label(user: Mapping[str, Any]) -> str:
    return f"{user.get('display_name', 'Demo user')} · {user.get('demo_user_id', '')}"


def _set_notice(kind: str, text: str) -> None:
    st.session_state["vs_insurance_notice"] = {"kind": kind, "text": text}


def _render_notice() -> None:
    notice = st.session_state.pop("vs_insurance_notice", None)
    if not isinstance(notice, Mapping):
        return
    text = str(notice.get("text", ""))
    kind = str(notice.get("kind", "info"))
    if not text:
        return
    if kind == "success":
        st.success(text)
    elif kind == "warning":
        st.warning(text)
    elif kind == "error":
        st.error(text)
    else:
        st.info(text)


def _on_user_change() -> None:
    st.session_state["vs_insurance_nominee_policy_id"] = None
    st.session_state["vs_insurance_review_policy_id"] = None
    st.session_state.pop("vs_insurance_notice", None)


def _reset_demo_callback() -> None:
    users = users_as_dicts()
    reset_insurance_session(
        st.session_state, users, seeded_nominee_links_as_dicts()
    )
    st.session_state["vs_insurance_notice"] = {
        "kind": "success",
        "text": (
            "Insurance demo reset. Seeded demo policies and the seeded nominee "
            "link are restored; session-created external records were removed."
        ),
    }


def _fact_grid(pairs: Sequence[tuple[str, object]]) -> None:
    cells = "".join(
        (
            '<div><span class="vs-fact-label">'
            f"{esc(label)}</span><strong>{esc(display_value(value))}</strong></div>"
        )
        for label, value in pairs
    )
    st.markdown(f'<div class="vs-fact-grid">{cells}</div>', unsafe_allow_html=True)


def _product_label(value: object) -> str:
    text = str(value or "unknown")
    return text.replace("_", " ").title()


def _render_session_card(user: Mapping[str, Any], users: Sequence[Mapping[str, Any]]) -> None:
    st.markdown("#### Demo Paytm session")
    st.caption(PAYTM_SESSION_NOTE)
    user_ids = [str(item["demo_user_id"]) for item in users]
    st.selectbox(
        "Switch demo Paytm user",
        options=user_ids,
        format_func=lambda value: _user_label(
            find_demo_user(users, value) or {"display_name": value, "demo_user_id": value}
        ),
        key="vs_insurance_active_user_id",
        on_change=_on_user_change,
    )
    st.markdown(
        f"""
        <div class="vs-session-card">
          <div class="vs-session-avatar">{esc(user.get('initials', 'D'))}</div>
          <div>
            <div class="vs-session-name">{esc(user.get('display_name', 'Demo user'))}</div>
            <div class="vs-mono">{esc(user.get('demo_user_id', ''))}</div>
            <div style="margin-top:6px;">
              {pill('DEMO SESSION', 'vs-pill-paytm')}
              {pill('No real authentication', 'vs-pill-neutral')}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _policy_detail_rows(record: Mapping[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Policyholder", record.get("policyholder_name")),
        ("Insured persons", ", ".join(record.get("insured_persons") or [])),
        ("UIN", record.get("uin")),
        ("Policy number (masked)", record.get("policy_number_masked")),
        ("Premium frequency", record.get("premium_frequency")),
        ("Document name", record.get("document_name")),
        ("OCR nominee name", record.get("ocr_nominee_name")),
        ("OCR nominee relationship", record.get("ocr_nominee_relationship")),
    ]


def _render_link_status(link: Mapping[str, Any]) -> None:
    st.markdown(
        pill(nominee_status_label(link), "vs-pill-review")
        + " "
        + pill("DEMO LINK", "vs-pill-demo"),
        unsafe_allow_html=True,
    )
    owner = demo_user_by_id(str(link.get("owner_demo_user_id", "")))
    nominee = demo_user_by_id(str(link.get("nominee_demo_user_id", "")))
    sharing = (
        "Limited summary sharing allowed"
        if link.get("owner_authorised_summary_sharing")
        else "Limited summary sharing off"
    )
    st.caption(
        f"Owner: {owner.get('display_name') if owner else 'Demo owner'} · "
        f"Nominee: {nominee.get('display_name') if nominee else 'Demo nominee'} · "
        f"Relationship: {relationship_label(link.get('relationship'))} · {sharing}"
    )
    st.caption("Insurer nomination not verified. This demo link is not a legal nomination.")


def _link_rows(link: Mapping[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Demo link ID", link.get("link_id")),
        ("Relationship", relationship_label(link.get("relationship"))),
        ("Summary sharing", "Allowed" if link.get("owner_authorised_summary_sharing") else "Off"),
        ("Note", link.get("note")),
        ("Updated", link.get("updated_at")),
    ]


def _render_nominee_panel(
    policy: Mapping[str, Any],
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
) -> None:
    policy_id = str(policy["policy_id"])
    existing = active_nominee_link_for_policy(links, policy_id)
    st.markdown(warning_box(NOMINEE_LEGAL_WORDING), unsafe_allow_html=True)
    st.write("")
    if existing is not None:
        _render_link_status(existing)
        _fact_grid(_link_rows(existing))
        action, cancel = st.columns(2)
        with action:
            if st.button(
                "Revoke demo sharing link",
                key=f"vs_revoke_link_{existing.get('link_id')}",
                width="stretch",
            ):
                try:
                    updated = revoke_nominee_link(
                        existing,
                        owner_demo_user_id=str(owner["demo_user_id"]),
                    )
                    st.session_state["vs_insurance_links"] = replace_link(
                        links, updated
                    )
                    _set_notice(
                        "success",
                        "Demo sharing link revoked. This does not cancel an insurer "
                        "nomination.",
                    )
                    st.session_state["vs_insurance_nominee_policy_id"] = None
                    st.rerun()
                except NomineeError as exc:
                    st.error(str(exc))
        with cancel:
            if st.button(
                "Close nominee panel",
                key=f"vs_close_nominee_{policy_id}",
                width="stretch",
            ):
                st.session_state["vs_insurance_nominee_policy_id"] = None
                st.rerun()
        st.caption(
            "Revoking removes the limited summary from the nominee's demo view; "
            "it is not an insurer nomination cancellation."
        )
        return

    candidates = [
        dict(user)
        for user in users
        if user.get("demo_user_id") != owner.get("demo_user_id")
    ]
    if not candidates:
        st.info("There is no other seeded demo user to select as a nominee.")
        return
    candidate_ids = [str(user["demo_user_id"]) for user in candidates]
    selected_id = st.selectbox(
        "Nominee demo Paytm ID",
        options=candidate_ids,
        format_func=lambda value: _user_label(
            find_demo_user(users, value) or {"display_name": value, "demo_user_id": value}
        ),
        key=f"vs_nominee_user_{policy_id}",
        help="Only seeded mock Paytm IDs are searched. No Paytm lookup is made.",
    )
    matched = find_demo_user(users, selected_id)
    if matched is not None:
        st.markdown(
            pill("Demo nominee selected", "vs-pill-paytm")
            + " "
            + pill("Seeded mock directory only", "vs-pill-demo"),
            unsafe_allow_html=True,
        )
        st.caption(
            f"Matched fictional profile: {matched.get('display_name')} · "
            f"{matched.get('demo_user_id')}"
        )
    relationship = st.selectbox(
        "Relationship",
        options=list(RELATIONSHIP_OPTIONS),
        format_func=relationship_label,
        key=f"vs_nominee_relationship_{policy_id}",
    )
    note = st.text_area(
        "Optional note (stored in this demo session only)",
        key=f"vs_nominee_note_{policy_id}",
        max_chars=300,
        height=80,
    )
    owner_confirmed = st.checkbox(
        "I confirm I am the policyholder and I want to create this simulated "
        "Paytm-ID nominee link.",
        value=False,
        key=f"vs_nominee_consent_{policy_id}",
    )
    share_summary = st.checkbox(
        "Allow this demo nominee to see a limited policy summary after they accept.",
        value=False,
        key=f"vs_nominee_share_{policy_id}",
        help=(
            "Off by default. Nomination and summary sharing are separate consent "
            "decisions. The full policy document, premium and full policy number are "
            "not shared."
        ),
    )
    st.caption(
        "Creating the demo link does not give the nominee access by itself. The "
        "nominee must accept, and the separate sharing checkbox must be on."
    )
    submit, cancel = st.columns(2)
    with submit:
        create_clicked = st.button(
            "Create simulated nominee link",
            key=f"vs_create_nominee_{policy_id}",
            type="primary",
            disabled=not owner_confirmed,
            width="stretch",
        )
    with cancel:
        if st.button(
            "Cancel",
            key=f"vs_cancel_nominee_{policy_id}",
            width="stretch",
        ):
            st.session_state["vs_insurance_nominee_policy_id"] = None
            st.rerun()

    if create_clicked:
        try:
            link = create_nominee_link(
                policy=policy,
                owner_demo_user_id=str(owner["demo_user_id"]),
                nominee_demo_user_id=selected_id,
                relationship=relationship,
                note=note,
                owner_confirmed=owner_confirmed,
                share_summary=share_summary,
                users=users,
                existing_links=links,
            )
        except NomineeError as exc:
            st.error(str(exc))
            return
        st.session_state["vs_insurance_links"] = list(links) + [link]
        _set_notice("success", link_created_message(link))
        st.session_state["vs_insurance_nominee_policy_id"] = None
        st.rerun()


def _render_policy_card(
    record: Mapping[str, Any],
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
    extra_badge: str | None = None,
) -> None:
    policy_id = str(record["policy_id"])
    with st.container(border=True):
        st.markdown(
            f'<div class="vs-insurer-name">{esc(display_value(record.get("insurer_name")))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            pill(source_label(record.get("source_type")), "vs-pill-paytm")
            + " "
            + pill(verification_label(record.get("verification_status")), "vs-pill-review")
            + (" " + pill(extra_badge, "vs-pill-demo") if extra_badge else ""),
            unsafe_allow_html=True,
        )
        st.markdown(f"**{esc(display_value(record.get('product_name')))}**")
        _fact_grid(
            [
                ("Insurance type", _product_label(record.get("product_type"))),
                ("Policy number (masked)", record.get("policy_number_masked")),
                (
                    "Policy period",
                    f"{display_date(record.get('policy_start_date'))} – "
                    f"{display_date(record.get('policy_end_date'))}",
                ),
                ("Sum insured / coverage", record.get("sum_insured")),
                ("Premium", record.get("premium_amount")),
                ("Premium frequency", record.get("premium_frequency")),
            ]
        )
        st.caption(f"Source: {source_label(record.get('source_type'))}")
        st.caption(f"Status: {verification_label(record.get('verification_status'))}")
        st.caption(str(record.get("display_status", "")))

        existing = active_nominee_link_for_policy(links, policy_id)
        if existing is not None:
            st.markdown(
                pill(nominee_status_label(existing), "vs-pill-review"),
                unsafe_allow_html=True,
            )

        detail_col, action_col = st.columns([0.62, 0.38])
        with detail_col:
            with st.expander("View details"):
                _fact_grid(_policy_detail_rows(record))
                st.caption(
                    "The full policy number is not shown in this summary. All values "
                    "are demo data or OCR output and are not insurer-verified."
                )
        with action_col:
            if can_manage_nominee(record):
                label = "Manage nominee" if existing is None else "View nominee link"
                if st.button(
                    label,
                    key=f"vs_manage_nominee_{policy_id}",
                    width="stretch",
                ):
                    st.session_state["vs_insurance_nominee_policy_id"] = policy_id
                    st.rerun()
            else:
                st.caption("Review and confirm this policy before adding a nominee.")

        if st.session_state.get("vs_insurance_nominee_policy_id") == policy_id:
            st.divider()
            _render_nominee_panel(
                record,
                users=users,
                owner=owner,
                links=links,
            )


def _render_bought(
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
) -> None:
    st.markdown("### Bought on Paytm")
    st.caption(
        "Seeded fictional policies attached to the currently selected demo user. "
        "No Paytm API is called and no real policy is shown."
    )
    policies = paytm_policies_for_user(seeded_paytm_records(), str(owner["demo_user_id"]))
    if not policies:
        st.info("This demo user has no seeded Bought on Paytm policies.")
        return
    st.markdown(
        pill(f"{len(policies)} demo policies", "vs-pill-paytm")
        + " "
        + pill("SIMULATED_NOT_VERIFIED", "vs-pill-review"),
        unsafe_allow_html=True,
    )
    st.write("")
    for record in policies:
        _render_policy_card(
            record,
            users=users,
            owner=owner,
            links=links,
            extra_badge="DEMO DATA",
        )


def _render_review_form(record: Mapping[str, Any]) -> None:
    policy_id = str(record["policy_id"])
    st.markdown("#### Review extracted details")
    st.caption(
        "Correct only what the document actually says. Blank fields are saved as "
        "Not found in document. The policy number is masked after saving."
    )
    with st.form(f"vs_review_form_{policy_id}"):
        insurer_name = st.text_input(
            "Insurer name",
            value=str(record.get("insurer_name") or ""),
            key=f"vs_review_insurer_{policy_id}",
        )
        product_name = st.text_input(
            "Product / plan name",
            value=str(record.get("product_name") or ""),
            key=f"vs_review_product_{policy_id}",
        )
        current_product = str(record.get("product_type") or "unknown")
        product_index = (
            PRODUCT_TYPES.index(current_product)
            if current_product in PRODUCT_TYPES
            else PRODUCT_TYPES.index("unknown")
        )
        product_type = st.selectbox(
            "Insurance type",
            options=list(PRODUCT_TYPES),
            index=product_index,
            format_func=_product_label,
            key=f"vs_review_type_{policy_id}",
        )
        policy_number = st.text_input(
            "Policy number (full value used only for this review)",
            value=str(record.get("policy_number_full") or ""),
            key=f"vs_review_number_{policy_id}",
        )
        uin = st.text_input(
            "UIN, if printed",
            value=str(record.get("uin") or ""),
            key=f"vs_review_uin_{policy_id}",
        )
        date_col_1, date_col_2 = st.columns(2)
        with date_col_1:
            start_date = st.text_input(
                "Policy start date (YYYY-MM-DD)",
                value=str(record.get("policy_start_date") or ""),
                key=f"vs_review_start_{policy_id}",
            )
        with date_col_2:
            end_date = st.text_input(
                "Policy end date (YYYY-MM-DD)",
                value=str(record.get("policy_end_date") or ""),
                key=f"vs_review_end_{policy_id}",
            )
        sum_insured = st.text_input(
            "Sum insured / coverage, as printed",
            value=str(record.get("sum_insured") or ""),
            key=f"vs_review_sum_{policy_id}",
        )
        premium_amount = st.text_input(
            "Premium amount, as printed",
            value=str(record.get("premium_amount") or ""),
            key=f"vs_review_premium_{policy_id}",
        )
        premium_frequency = st.text_input(
            "Premium frequency, if printed",
            value=str(record.get("premium_frequency") or ""),
            key=f"vs_review_frequency_{policy_id}",
        )
        policyholder_name = st.text_input(
            "Policyholder name, as printed",
            value=str(record.get("policyholder_name") or ""),
            key=f"vs_review_holder_{policy_id}",
        )
        insured_persons = st.text_input(
            "Insured persons, as printed (comma-separated)",
            value=", ".join(record.get("insured_persons") or []),
            key=f"vs_review_insured_{policy_id}",
        )
        nominee_name = st.text_input(
            "Nominee name printed on document, if any",
            value=str(record.get("ocr_nominee_name") or ""),
            key=f"vs_review_nominee_name_{policy_id}",
        )
        nominee_relationship = st.text_input(
            "Nominee relationship printed on document, if any",
            value=str(record.get("ocr_nominee_relationship") or ""),
            key=f"vs_review_nominee_rel_{policy_id}",
        )
        authorised = st.checkbox(
            "I confirm this document is mine, or I am authorised to add it to this "
            "demo session.",
            value=False,
            key=f"vs_review_authorised_{policy_id}",
        )
        st.caption(
            "Saving marks the record USER_REVIEWED_UNVERIFIED. It does not verify the "
            "policy with the insurer or confirm that it is active."
        )
        # Do not disable the submit button inside an st.form: widget changes
        # inside a form are not sent until submit, so a disabled button would
        # never become clickable after the user ticks the confirmation box.
        submitted = st.form_submit_button(
            "Save review and confirm record",
            type="primary",
        )

    if submitted:
        updates = {
            "insurer_name": insurer_name,
            "product_name": product_name,
            "product_type": product_type,
            "policy_number_full": policy_number,
            "uin": uin,
            "policy_start_date": start_date,
            "policy_end_date": end_date,
            "sum_insured": sum_insured,
            "premium_amount": premium_amount,
            "premium_frequency": premium_frequency,
            "policyholder_name": policyholder_name,
            "insured_persons": insured_persons,
            "ocr_nominee_name": nominee_name,
            "ocr_nominee_relationship": nominee_relationship,
        }
        try:
            updated = review_external_policy(
                record, updates, authorised=authorised
            )
        except ValueError as exc:
            st.error(str(exc))
            return
        external = [
            updated if item.get("policy_id") == policy_id else dict(item)
            for item in st.session_state.get("vs_insurance_external_policies", [])
        ]
        st.session_state["vs_insurance_external_policies"] = external
        st.session_state["vs_insurance_review_policy_id"] = None
        _set_notice(
            "success",
            "External policy marked USER_REVIEWED_UNVERIFIED. Insurer status is "
            "still not verified.",
        )
        st.rerun()


def _remove_external(policy_id: str) -> None:
    remove_external_policy_session(st.session_state, policy_id)
    if st.session_state.get("vs_insurance_review_policy_id") == policy_id:
        st.session_state["vs_insurance_review_policy_id"] = None
    _set_notice(
        "success",
        "External document record removed from this session, along with any demo "
        "nominee link attached to it.",
    )
    st.rerun()


def _render_external_record(
    record: Mapping[str, Any],
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
) -> None:
    policy_id = str(record["policy_id"])
    needs_review = external_record_is_reviewable(record)
    if not needs_review:
        _render_policy_card(
            record,
            users=users,
            owner=owner,
            links=links,
            extra_badge="USER REVIEWED",
        )
        if st.button(
            "Remove document / policy from this session",
            key=f"vs_remove_external_{policy_id}",
        ):
            _remove_external(policy_id)
        return

    with st.container(border=True):
        st.markdown(
            f'<div class="vs-insurer-name">{esc(display_value(record.get("insurer_name")))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            pill("External Insurance — DEMO OCR", "vs-pill-paytm")
            + " "
            + pill("NEEDS REVIEW", "vs-pill-review")
            + " "
            + pill("OCR_EXTRACTED_NEEDS_REVIEW", "vs-pill-demo"),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**{esc(display_value(record.get('product_name')))}**"
        )
        _fact_grid(
            [
                ("Insurance type", _product_label(record.get("product_type"))),
                ("Policy number (masked)", record.get("policy_number_masked")),
                (
                    "Policy period",
                    f"{display_date(record.get('policy_start_date'))} – "
                    f"{display_date(record.get('policy_end_date'))}",
                ),
                ("Sum insured / coverage", record.get("sum_insured")),
                ("Premium", record.get("premium_amount")),
                ("Document", record.get("document_name")),
            ]
        )
        st.caption(f"Status: {verification_label(record.get('verification_status'))}")
        st.caption(str(record.get("display_status", "")))
        reasons = record.get("review_reasons") or []
        if reasons:
            st.markdown("**Why this needs review**")
            for reason in reasons:
                st.caption(f"• {reason}")
        st.markdown(warning_box(OCR_REVIEW_NOTE), unsafe_allow_html=True)
        with st.expander("Raw extracted values (session only)"):
            st.json(record.get("raw_extracted") or {})
            st.caption(
                "Kept only in this browser session for review. It is not written to "
                "logs, a cache or the repository."
            )
        action_col, remove_col = st.columns(2)
        with action_col:
            if st.button(
                "Review extracted details",
                key=f"vs_review_open_{policy_id}",
                type="primary",
                width="stretch",
            ):
                st.session_state["vs_insurance_review_policy_id"] = policy_id
                st.rerun()
        with remove_col:
            if st.button(
                "Remove document / policy from this session",
                key=f"vs_remove_external_{policy_id}",
                width="stretch",
            ):
                _remove_external(policy_id)
        if st.session_state.get("vs_insurance_review_policy_id") == policy_id:
            st.divider()
            _render_review_form(record)


def _process_upload(
    uploaded: Any,
    *,
    config: DocumentAiConfig,
    language: str,
    owner: Mapping[str, Any],
) -> None:
    raw = uploaded.getvalue()
    try:
        validated = validate_insurance_upload(uploaded.name, raw)
    except UploadValidationError as exc:
        st.error(str(exc))
        st.info("No policy was added. Seeded demo policies remain available.")
        return

    status = st.status("Processing with Sarvam Document AI…", expanded=True)
    try:
        service = SarvamDocumentAI(config)
        outcome = service.extract_policy(
            raw,
            filename=validated.filename,
            mime_type=validated.mime_type,
            language=language,
            progress=lambda stage, message: status.write(message),
        )
        status.update(label="Sarvam extraction completed", state="complete")
    except DocumentAiError as exc:
        status.update(label="Sarvam extraction failed", state="error")
        st.error(str(exc))
        st.info(
            "No policy was added. Seeded demo policies remain available; upload "
            "again after fixing the issue."
        )
        return
    finally:
        # The request is complete. Drop our local reference to the bytes.
        del raw

    result = build_external_policy(
        outcome.result,
        document_name=validated.filename,
        owner_demo_user_id=str(owner["demo_user_id"]),
    )
    if not result.added or result.record is None:
        st.error(result.message)
        st.info("No policy was added. Seeded demo policies remain available.")
        return

    external = list(st.session_state.get("vs_insurance_external_policies", []))
    external.append(result.record)
    st.session_state["vs_insurance_external_policies"] = external
    st.session_state["vs_insurance_review_policy_id"] = result.record["policy_id"]
    st.session_state["vs_insurance_upload_nonce"] = (
        int(st.session_state.get("vs_insurance_upload_nonce", 0)) + 1
    )
    message = result.message
    if outcome.partial:
        message += (
            " Sarvam returned partially completed results; missing fields remain "
            "Not found in document."
        )
    _set_notice("success", message)
    st.rerun()


def _render_upload_panel(owner: Mapping[str, Any]) -> None:
    config = DocumentAiConfig.from_env()
    st.markdown("### Add an external policy document")
    st.caption(
        "PDF, PNG, JPG or JPEG only · maximum 10 MB · maximum 20 PDF pages. "
        "The file is held in memory for this request and is not saved."
    )
    if not config.has_api_key:
        st.warning("Add SARVAM_API_KEY to .env to enable document extraction.")
    elif not config.is_configured:
        st.warning(config.disabled_message)
    else:
        st.success(config.disabled_message)

    st.markdown(warning_box(UPLOAD_DISCLOSURE), unsafe_allow_html=True)
    nonce = int(st.session_state.get("vs_insurance_upload_nonce", 0))
    acknowledged = st.checkbox(
        "I have read and understand this disclosure, and I am authorised to share "
        "this document.",
        value=False,
        key=f"vs_insurance_upload_ack_{nonce}",
    )
    uploaded = st.file_uploader(
        "Upload insurance policy document",
        type=["pdf", "png", "jpg", "jpeg"],
        disabled=not acknowledged or not config.is_configured,
        key=f"vs_insurance_upload_{nonce}",
        help="Do not upload real customer documents to this hackathon prototype.",
    )
    language_options = list(ALLOWED_DOCUMENT_LANGUAGES)
    language_index = (
        language_options.index(config.language)
        if config.language in language_options
        else 0
    )
    language = st.selectbox(
        "Document language",
        options=language_options,
        index=language_index,
        format_func=lambda value: {
            "en-IN": "English (en-IN)",
            "hi-IN": "Hindi (hi-IN)",
            "bn-IN": "Bengali (bn-IN)",
        }.get(value, value),
        key="vs_insurance_ocr_language",
        disabled=not config.is_configured,
    )
    st.caption(
        "Sarvam Extract is asynchronous: the app submits the job, polls its status "
        "and then retrieves structured results."
    )
    process = st.button(
        "Process document",
        key="vs_insurance_process",
        type="primary",
        disabled=not acknowledged or uploaded is None or not config.is_configured,
    )
    if process and uploaded is not None and acknowledged:
        _process_upload(
            uploaded,
            config=config,
            language=language,
            owner=owner,
        )


def _render_external(
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
) -> None:
    st.markdown("### External Insurance")
    st.caption(
        "Documents you upload are processed by Sarvam Document AI Extract. A "
        "successful extraction creates a Needs review record automatically. OCR "
        "output is never treated as insurer confirmation."
    )
    _render_upload_panel(owner)
    st.divider()
    st.markdown("### External policies in this session")
    external = external_policies_for_user(
        st.session_state.get("vs_insurance_external_policies", []),
        str(owner["demo_user_id"]),
    )
    if not external:
        st.info(
            "No external policies in this session for this demo user. Upload a "
            "document above, or use the seeded Bought on Paytm policies for the demo."
        )
        return
    for record in external:
        _render_external_record(
            record,
            users=users,
            owner=owner,
            links=links,
        )


def _render_limited_summary(
    summary: Mapping[str, Any],
    *,
    owner_name: str,
) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="vs-insurer-name">{esc(display_value(summary.get("insurer_name")))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            pill("Limited summary shared by owner", "vs-pill-shared")
            + " "
            + pill("Demo link accepted", "vs-pill-paytm")
            + " "
            + pill("DEMO SUMMARY", "vs-pill-demo"),
            unsafe_allow_html=True,
        )
        st.markdown(f"**{esc(display_value(summary.get('product_name')))}**")
        _fact_grid(
            [
                ("Shared by", owner_name),
                ("Insurance type", _product_label(summary.get("product_type"))),
                ("Policy number (masked)", summary.get("policy_number_masked")),
                (
                    "Policy period",
                    f"{display_date(summary.get('policy_start_date'))} – "
                    f"{display_date(summary.get('policy_end_date'))}",
                ),
                ("Sum insured / coverage", summary.get("sum_insured")),
            ]
        )
        st.caption(str(summary.get("display_status", "")))
        st.caption(
            "Limited summary only. The full policy document, premium and full policy "
            "number are not shared. Insurer nomination not verified."
        )


def _respond_to_link(
    link: Mapping[str, Any],
    *,
    nominee: Mapping[str, Any],
    accept: bool,
) -> None:
    try:
        updated = respond_to_nominee_link(
            link,
            nominee_demo_user_id=str(nominee["demo_user_id"]),
            accept=accept,
        )
    except NomineeError as exc:
        st.error(str(exc))
        return
    st.session_state["vs_insurance_links"] = replace_link(
        st.session_state.get("vs_insurance_links", []), updated
    )
    _set_notice(
        "success",
        (
            "Demo link accepted. Only an owner-authorised limited summary is shown."
            if accept
            else "Demo invitation declined. The demo link was revoked."
        ),
    )
    st.rerun()


def _render_nominee_section(
    *,
    users: Sequence[Mapping[str, Any]],
    owner: Mapping[str, Any],
    links: Sequence[Mapping[str, Any]],
) -> None:
    st.markdown("### Nominee-linked Policies")
    st.markdown(warning_box(NOMINEE_LEGAL_WORDING), unsafe_allow_html=True)
    st.caption(
        "Nomination and policy-summary sharing are separate consent decisions. A "
        "selected nominee does not see any policy details merely because they were "
        "selected."
    )
    records = all_policy_records(
        seeded_paytm_records(),
        st.session_state.get("vs_insurance_external_policies", []),
    )
    invitations = nominee_invitations_for_user(links, str(owner["demo_user_id"]))
    if invitations:
        st.markdown("#### Your demo nominee invitations")
        for link in invitations:
            policy = find_policy(records, str(link.get("policy_id", "")))
            owner_profile = demo_user_by_id(str(link.get("owner_demo_user_id", "")))
            owner_name = (
                str(owner_profile.get("display_name"))
                if owner_profile
                else "Demo owner"
            )
            acceptance = str(link.get("nominee_acceptance_status"))
            with st.container(border=True):
                st.markdown(
                    f'<div class="vs-insurer-name">Invitation from {esc(owner_name)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    pill(nominee_status_label(link), "vs-pill-review")
                    + " "
                    + pill("DEMO", "vs-pill-demo"),
                    unsafe_allow_html=True,
                )
                if acceptance == "PENDING":
                    st.caption(
                        "No policy details are shown while this invitation is pending. "
                        "Accepting does not share anything unless the owner explicitly "
                        "allowed a limited summary."
                    )
                    st.caption(
                        "Owner allowed limited summary sharing: "
                        + (
                            "Yes"
                            if link.get("owner_authorised_summary_sharing")
                            else "No (sharing is off)"
                        )
                    )
                    accept_col, decline_col = st.columns(2)
                    with accept_col:
                        if st.button(
                            "Accept demo link",
                            key=f"vs_accept_link_{link.get('link_id')}",
                            type="primary",
                            width="stretch",
                        ):
                            _respond_to_link(link, nominee=owner, accept=True)
                    with decline_col:
                        if st.button(
                            "Decline demo link",
                            key=f"vs_decline_link_{link.get('link_id')}",
                            width="stretch",
                        ):
                            _respond_to_link(link, nominee=owner, accept=False)
                else:
                    summary = limited_shared_summary(
                        link, records, str(owner["demo_user_id"])
                    )
                    if summary is not None:
                        _render_limited_summary(summary, owner_name=owner_name)
                    else:
                        st.info(
                            "Demo link accepted. The owner has not allowed a limited "
                            "policy summary to be shared, so no policy details are "
                            "shown."
                        )
                    st.caption(
                        "Insurer nomination not verified. This demo link does not "
                        "register or confirm a legal nominee."
                    )
            st.caption(str(link.get("note") or ""))
    else:
        st.info(
            f"No pending or accepted demo nominee invitations for "
            f"{owner.get('display_name')}."
        )

    owned_links = owner_links_for_user(links, str(owner["demo_user_id"]))
    if owned_links:
        st.markdown("#### Demo links you created")
        st.caption(
            "These are simulated Paytm-ID links inside this prototype. They are not "
            "insurer nomination records."
        )
        for link in owned_links:
            policy = find_policy(records, str(link.get("policy_id", "")))
            nominee = demo_user_by_id(str(link.get("nominee_demo_user_id", "")))
            with st.container(border=True):
                policy_label = (
                    display_value(policy.get("product_name"))
                    if policy
                    else "Policy not found in session"
                )
                st.markdown(
                    f'<div class="vs-insurer-name">{esc(policy_label)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    pill(nominee_status_label(link), "vs-pill-review")
                    + " "
                    + pill("DEMO LINK", "vs-pill-demo"),
                    unsafe_allow_html=True,
                )
                _fact_grid(
                    [
                        ("Nominee", nominee.get("display_name") if nominee else "Demo nominee"),
                        (
                            "Nominee demo Paytm ID",
                            nominee.get("demo_user_id") if nominee else None,
                        ),
                        ("Relationship", relationship_label(link.get("relationship"))),
                        (
                            "Limited summary sharing",
                            "Allowed" if link.get("owner_authorised_summary_sharing") else "Off",
                        ),
                    ]
                )
                st.caption(
                    "Insurer nomination not verified. Revoking this link only changes "
                    "the demo sharing state; it does not cancel any insurer nomination."
                )
                if link.get("demo_link_status") == "ACTIVE":
                    if st.button(
                        "Revoke demo sharing link",
                        key=f"vs_revoke_owned_{link.get('link_id')}",
                    ):
                        try:
                            updated = revoke_nominee_link(
                                link,
                                owner_demo_user_id=str(owner["demo_user_id"]),
                            )
                        except NomineeError as exc:
                            st.error(str(exc))
                        else:
                            st.session_state["vs_insurance_links"] = replace_link(
                                links, updated
                            )
                            _set_notice(
                                "success",
                                "Demo sharing link revoked. The limited summary is no "
                                "longer visible to the nominee.",
                            )
                            st.rerun()


def render_active_insurances(language: str = "en") -> None:
    """Render the complete Active Insurances dashboard."""
    users = users_as_dicts()
    ensure_insurance_session(
        st.session_state, users, seeded_nominee_links_as_dicts()
    )
    owner = _active_user(users)
    links = list(st.session_state.get("vs_insurance_links", []))

    if st.button("← Back to home", key="vs_insurance_back"):
        st.session_state["vs_page"] = "home"
        st.rerun()

    st.markdown("## Active Insurances")
    st.caption(
        "A Paytm-style demo inventory for policies bought on Paytm, external "
        "documents processed with Sarvam Document AI, and explicitly shared "
        "nominee-linked summaries."
    )
    st.markdown(
        f'<div class="vs-paytm-strip">{esc(PROTOTYPE_LABEL)}</div>',
        unsafe_allow_html=True,
    )
    _render_notice()
    _render_session_card(owner, users)

    st.write("")
    section = st.radio(
        "Active Insurances section",
        options=list(SECTION_LABELS.keys()),
        format_func=lambda value: SECTION_LABELS[value],
        horizontal=True,
        key="vs_insurance_section",
        label_visibility="collapsed",
    )

    if section == "external":
        _render_external(users=users, owner=owner, links=links)
    elif section == "nominee":
        _render_nominee_section(users=users, owner=owner, links=links)
    else:
        _render_bought(users=users, owner=owner, links=links)

    st.divider()
    st.caption(
        "Demo boundary: Paytm data and nominee links are simulated. Sarvam OCR "
        "output is fallible and unverified. No insurer confirmation, claim filing, "
        "payment or legal nomination is implemented in this prototype."
    )
    st.button(
        "Reset insurance demo",
        key="vs_insurance_reset_demo",
        on_click=_reset_demo_callback,
        help=(
            "Clears session-created external policies and nominee changes, then "
            "restores the seeded demo fixtures."
        ),
    )


__all__ = ["render_active_insurances"]
