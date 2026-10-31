"""UI components for Family Claim Orchestrator."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import streamlit as st

from src.claim_orchestrator import (
    EventRelevance,
    ClaimantCapacity,
    WorkflowState,
    classify_policy_event_relevance,
    create_family_claim_batch,
    get_batches,
    get_workflows,
    get_common_documents,
    add_common_document,
    map_document_to_workflow,
    add_workflow_timeline_event,
    save_workflow_draft,
    update_workflow_status,
    load_playbook,
    get_playbook_for_relevance,
    PolicyClaimWorkflow,
    FamilyClaimBatch,
)
from src.insurance_inventory import (
    seeded_paytm_records,
    find_policy,
    display_date,
    display_value,
    source_label,
    verification_label,
)
from src.mock_paytm_data import demo_user_by_id

EVENT_RELEVANCE_LABELS: dict[str, str] = {
    "POTENTIAL_LIFE_DEATH_CLAIM": "Potential life death-claim",
    "POTENTIAL_ACCIDENTAL_DEATH_BENEFIT": "Potential accidental death benefit",
    "CREDIT_LIFE_ENQUIRY": "Credit-life enquiry",
    "OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY": "Outstanding medical expense enquiry",
    "MOTOR_ACCIDENT_COVER_REVIEW": "Motor accident cover review",
    "NOT_INDICATED_BY_AVAILABLE_RECORDS": "No indicated route from available records",
    "INSUFFICIENT_EVIDENCE": "Insufficient evidence to determine",
}

EVENT_RELEVANCE_COLORS: dict[str, str] = {
    "POTENTIAL_LIFE_DEATH_CLAIM": "#0B5C55",
    "POTENTIAL_ACCIDENTAL_DEATH_BENEFIT": "#0B5C55",
    "CREDIT_LIFE_ENQUIRY": "#7A5200",
    "OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY": "#0B5C55",
    "MOTOR_ACCIDENT_COVER_REVIEW": "#7A5200",
    "NOT_INDICATED_BY_AVAILABLE_RECORDS": "#5B6B7A",
    "INSUFFICIENT_EVIDENCE": "#5B6B7A",
}

CAPACITY_LABELS: dict[str, str] = {
    "RECORDED_NOMINEE_IN_DEMO": "Recorded nominee (demo)",
    "AUTHORISED_REPRESENTATIVE_DEMO": "Authorised representative (demo)",
    "LEGAL_HEIR_CLAIMANT_UNVERIFIED": "Legal heir claimant (unverified)",
    "OTHER": "Other",
    "UNSURE": "Unsure",
}

WORKFLOW_STATE_LABELS: dict[str, str] = {
    "DISCOVERED": "Discovered",
    "RELEVANCE_REVIEW": "Relevance review",
    "CHECKLIST_READY": "Checklist ready",
    "DOCUMENTS_IN_PROGRESS": "Documents in progress",
    "READY_FOR_USER_REVIEW": "Ready for user review",
    "DRAFT_PREPARED": "Draft prepared",
    "USER_MARKED_SUBMITTED": "User marked submitted",
    "FOLLOW_UP": "Follow-up",
    "USER_MARKED_RESOLVED": "User marked resolved",
    "INSURER_QUERY_RECORDED": "Insurer query recorded",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pill(text: str, css_class: str = "vs-pill-neutral") -> str:
    return f'<span class="vs-pill {css_class}">{esc(text)}</span>'


def _render_relevance_badge(relevance: EventRelevance) -> str:
    color = EVENT_RELEVANCE_COLORS.get(relevance, "#5B6B7A")
    label = EVENT_RELEVANCE_LABELS.get(relevance, relevance)
    return f'<span class="vs-pill" style="background: {color}20; color: {color}; border: 1px solid {color}40;">{esc(label)}</span>'


def _render_capacity_badge(capacity: ClaimantCapacity) -> str:
    return pill(CAPACITY_LABELS.get(capacity, capacity), "vs-pill-info")


def _render_state_badge(state: WorkflowState) -> str:
    colors = {
        "DISCOVERED": "vs-pill-neutral",
        "RELEVANCE_REVIEW": "vs-pill-review",
        "CHECKLIST_READY": "vs-pill-info",
        "DOCUMENTS_IN_PROGRESS": "vs-pill-paytm",
        "READY_FOR_USER_REVIEW": "vs-pill-info",
        "DRAFT_PREPARED": "vs-pill-paytm",
        "USER_MARKED_SUBMITTED": "vs-pill-review",
        "FOLLOW_UP": "vs-pill-paytm",
        "USER_MARKED_RESOLVED": "vs-pill-shared",
        "INSURER_QUERY_RECORDED": "vs-pill-review",
    }
    return pill(WORKFLOW_STATE_LABELS.get(state, state), colors.get(state, "vs-pill-neutral"))


def render_family_claim_orchestrator(
    *,
    claimant_demo_user_id: str,
    deceased_demo_user_id: str,
    family_case_id: str,
    event_type: str = "DEATH",
    event_date: date | None = None,
) -> None:
    """Render the Family Claim Orchestrator view within an approved Family Claims case."""
    from datetime import date as dt_date

    if event_date is None:
        event_date = dt_date.today()

    st.markdown("## Family Claim Orchestrator — One Event, Multiple Policies")
    st.info(
        "This tool analyses all policies linked to the deceased demo profile and creates "
        "separate, policy-specific claim-preparation workflows. Each workflow has its own "
        "checklist, documents, draft and timeline. No insurer status is implied."
    )
    st.divider()

    # Event summary
    st.markdown("### Event details")
    deceased = demo_user_by_id(deceased_demo_user_id)
    claimant = demo_user_by_id(claimant_demo_user_id)
    cols = st.columns(3)
    with cols[0]:
        st.write(f"**Deceased:** {esc(deceased.get('display_name', 'Unknown'))}")
        st.caption(f"@{esc(deceased.get('demo_user_id', ''))}")
    with cols[1]:
        st.write(f"**Event:** {esc(event_type)}")
        st.caption(f"Date: {esc(event_date.isoformat())}")
    with cols[2]:
        st.write(f"**Claimant:** {esc(claimant.get('display_name', 'Unknown'))}")
        st.caption(f"@{esc(claimant.get('demo_user_id', ''))}")

    st.divider()

    # Load policies for deceased
    policies = seeded_paytm_records()
    deceased_policies = [p for p in policies if p.get("owner_demo_user_id") == deceased_demo_user_id]

    if not deceased_policies:
        st.warning("No policies found for the deceased demo profile.")
        return

    # Step 1: Analyse policies for this event
    st.markdown("### Policy relevance analysis")
    st.caption(
        "Each policy is evaluated against the event. A death event does not make every policy "
        "a death-benefit claim. The rules are deterministic and based on product type, "
        "insured person match, policy dates, and available evidence."
    )

    if st.button("Analyse policies for this event", key="vs_fco_analyse", type="primary", width="stretch"):
        relevance_results = []
        for policy in deceased_policies:
            relevance, evidence = classify_policy_event_relevance(
                policy, event_type, event_date, deceased_demo_user_id, []
            )
            playbook_id = get_playbook_for_relevance(relevance, policy.get("product_type", "unknown"))

            # Determine claimant capacity
            capacity: ClaimantCapacity = "UNSURE"
            if policy.get("ocr_nominee_name") and claimant_demo_user_id in str(policy.get("ocr_nominee_name", "")).lower():
                capacity = "RECORDED_NOMINEE_IN_DEMO"
            elif policy.get("policyholder_name") and claimant_demo_user_id in str(policy.get("policyholder_name", "")).lower():
                capacity = "AUTHORISED_REPRESENTATIVE_DEMO"

            relevance_results.append({
                "policy": policy,
                "relevance": relevance,
                "evidence": evidence,
                "capacity": capacity,
                "playbook_id": playbook_id,
            })

        st.session_state["vs_fco_relevance_results"] = relevance_results
        st.rerun()

    # Display relevance matrix
    if "vs_fco_relevance_results" in st.session_state:
        relevance_results = st.session_state["vs_fco_relevance_results"]

        st.markdown("### Policy relevance matrix")
        for result in relevance_results:
            policy = result["policy"]
            relevance = result["relevance"]
            evidence = result["evidence"]
            capacity = result["capacity"]
            playbook_id = result["playbook_id"]

            with st.container(border=True):
                cols = st.columns([2, 1, 1, 1.5])
                with cols[0]:
                    st.markdown(f"**{esc(display_value(policy.get('product_name')))}**")
                    st.caption(f"{esc(source_label(policy.get('source_type')))} · {esc(verification_label(policy.get('verification_status')))}")
                    st.caption(f"Masked policy ID: {esc(policy.get('policy_number_masked', 'N/A'))}")
                with cols[1]:
                    st.markdown(_render_relevance_badge(relevance), unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(_render_capacity_badge(capacity), unsafe_allow_html=True)
                with cols[3]:
                    st.caption(f"Playbook: {esc(playbook_id) if playbook_id else 'N/A'}")

                with st.expander("View evidence"):
                    for ev in evidence:
                        st.markdown(
                            f'<div class="vs-evidence"><strong>{esc(ev.get("label", ""))}:</strong> {esc(ev.get("value", ""))} '
                            f'<span class="vs-mono">[{esc(ev.get("source", ""))}]</span></div>',
                            unsafe_allow_html=True,
                        )

        # Step 2: Create claim workflows
        st.divider()
        st.markdown("### Create claim workflows")
        st.caption(
            "Select the policies for which you want to create claim-preparation workflows. "
            "Each selected policy will become an independent child workflow with its own "
            "checklist, documents, draft and timeline."
        )

        selected_policies = []
        for result in relevance_results:
            policy = result["policy"]
            policy_id = str(policy.get("policy_id", ""))
            relevance = result["relevance"]
            if relevance in {"POTENTIAL_LIFE_DEATH_CLAIM", "POTENTIAL_ACCIDENTAL_DEATH_BENEFIT",
                           "CREDIT_LIFE_ENQUIRY", "OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY",
                           "MOTOR_ACCIDENT_COVER_REVIEW"}:
                default = True
            else:
                default = False

            if st.checkbox(
                f"{esc(display_value(policy.get('product_name')))} — {EVENT_RELEVANCE_LABELS.get(relevance, relevance)}",
                key=f"vs_fco_select_{policy_id}",
                value=default,
            ):
                selected_policies.append(policy_id)

        if st.button("Preview selected workflows", key="vs_fco_preview", type="secondary", width="stretch"):
            if not selected_policies:
                st.warning("No policies selected.")
            else:
                st.session_state["vs_fco_selected_policies"] = selected_policies
                st.rerun()

    # Preview and create batch
    if "vs_fco_selected_policies" in st.session_state:
        st.markdown("### Preview: Child workflows to be created")
        selected = st.session_state["vs_fco_selected_policies"]
        policy_map = {str(p["policy_id"]): p for p in deceased_policies}

        for pid in selected:
            policy = policy_map.get(pid)
            if not policy:
                continue
            relevance, evidence = classify_policy_event_relevance(
                policy, event_type, event_date, deceased_demo_user_id, []
            )
            playbook_id = get_playbook_for_relevance(relevance, policy.get("product_type", "unknown"))

            with st.container(border=True):
                st.markdown(f"**{esc(display_value(policy.get('product_name')))}**")
                st.markdown(_render_relevance_badge(relevance), unsafe_allow_html=True)
                st.caption(f"Masked policy ID: {esc(policy.get('policy_number_masked', 'N/A'))}")
                st.caption(f"Playbook: {esc(playbook_id) if playbook_id else 'N/A'}")
                st.caption(f"Claimant capacity: {CAPACITY_LABELS.get('RECORDED_NOMINEE_IN_DEMO', 'UNSURE')}")

        st.write("")
        if st.button("Create selected claim workflows", key="vs_fco_create", type="primary", width="stretch"):
            batch = create_family_claim_batch(
                state=st.session_state,
                family_case_id=family_case_id,
                claimant_demo_user_id=claimant_demo_user_id,
                deceased_demo_user_id=deceased_demo_user_id,
                event_type=event_type,
                event_date=event_date,
                selected_policy_ids=selected,
            )
            st.session_state["vs_fco_current_batch_id"] = batch.batch_id
            st.session_state.pop("vs_fco_selected_policies", None)
            st.session_state.pop("vs_fco_relevance_results", None)
            st.success(f"Created family claim batch: {batch.batch_id}")
            st.rerun()

    # Step 3: Display parent batch dashboard
    if "vs_fco_current_batch_id" in st.session_state:
        batch_id = st.session_state["vs_fco_current_batch_id"]
        batches = get_batches(st.session_state)
        batch = next((b for b in batches if b.batch_id == batch_id), None)

        if batch:
            st.divider()
            st.markdown(f"## Family Claim Batch: {esc(batch.batch_id)}")
            st.caption(f"Status: {pill(batch.status, 'vs-pill-info')} · Created: {esc(batch.created_at)}")

            workflows = get_workflows(st.session_state)
            child_workflows = [w for w in workflows if w.batch_id == batch_id]

            if child_workflows:
                st.markdown("### Child workflows")
                for wf in child_workflows:
                    with st.container(border=True):
                        policy = find_policy(seeded_paytm_records(), wf.policy_id)
                        cols = st.columns([2, 1, 1, 1.5])
                        with cols[0]:
                            st.markdown(f"**{esc(display_value(policy.get('product_name') if policy else wf.policy_id))}**")
                            st.caption(f"Policy ID: {esc(wf.policy_id)}")
                        with cols[1]:
                            st.markdown(_render_relevance_badge(wf.event_relevance), unsafe_allow_html=True)
                        with cols[2]:
                            st.markdown(_render_state_badge(wf.status), unsafe_allow_html=True)
                        with cols[3]:
                            st.caption(f"Claimant capacity: {esc(CAPACITY_LABELS.get(wf.claimant_capacity, wf.claimant_capacity))}")

                        if st.button(
                            f"Open workflow {wf.workflow_id}",
                            key=f"vs_fco_open_{wf.workflow_id}",
                            width="stretch",
                        ):
                            st.session_state["vs_fco_current_workflow_id"] = wf.workflow_id
                            st.rerun()

    # Step 4: Child workflow detail view
    if "vs_fco_current_workflow_id" in st.session_state:
        wf_id = st.session_state["vs_fco_current_workflow_id"]
        workflows = get_workflows(st.session_state)
        wf = next((w for w in workflows if w.workflow_id == wf_id), None)

        if wf:
            st.divider()
            st.markdown(f"## Child Workflow: {esc(wf.workflow_id)}")

            policy = find_policy(seeded_paytm_records(), wf.policy_id)
            playbook = load_playbook(wf.playbook_id) if wf.playbook_id else None

            with st.container(border=True):
                cols = st.columns(3)
                with cols[0]:
                    st.write(f"**Policy:** {esc(display_value(policy.get('product_name') if policy else wf.policy_id))}")
                    st.caption(f"Masked ID: {esc(policy.get('policy_number_masked', 'N/A') if policy else 'N/A')}")
                with cols[1]:
                    st.write(f"**Event relevance:**")
                    st.markdown(_render_relevance_badge(wf.event_relevance), unsafe_allow_html=True)
                with cols[2]:
                    st.write(f"**Status:**")
                    st.markdown(_render_state_badge(wf.status), unsafe_allow_html=True)

                st.caption(f"**Claimant capacity:** {esc(CAPACITY_LABELS.get(wf.claimant_capacity, wf.claimant_capacity))} — *Not legal proof or insurer approval*")

            st.divider()

            # Evidence
            st.markdown("### Relevance evidence")
            for ev in wf.relevance_evidence:
                st.markdown(
                    f'<div class="vs-evidence"><strong>{esc(ev.get("label", ""))}:</strong> {esc(ev.get("value", ""))} '
                    f'<span class="vs-mono">[{esc(ev.get("source", ""))}]</span></div>',
                    unsafe_allow_html=True,
                )

            # Playbook / Checklist
            if playbook:
                st.divider()
                st.markdown(f"### Checklist — {esc(playbook.get('playbook_id', ''))}")
                st.caption("Illustrative checklist — confirm with the insurer")

                st.markdown("**Required documents:**")
                for doc in playbook.get("required_documents", []):
                    st.write(f"• {esc(doc.get('label', ''))} — *{esc(doc.get('source', ''))}*")

                if playbook.get("conditional_documents"):
                    st.markdown("**Conditional documents:**")
                    for doc in playbook.get("conditional_documents", []):
                        st.write(f"• {esc(doc.get('label', ''))} — *Condition: {esc(doc.get('condition', ''))}*")

            # Documents
            st.divider()
            st.markdown("### Documents for this workflow")

            # Show mapped common documents
            common_docs = get_common_documents(st.session_state)
            mapped_docs = [d for d in common_docs if wf_id in d.get("mapped_workflow_ids", [])]

            if mapped_docs:
                for doc in mapped_docs:
                    with st.container(border=True):
                        st.write(f"**{esc(doc.get('file_name', ''))}** ({esc(doc.get('category', ''))})")
                        st.caption(f"MIME: {esc(doc.get('mime_type', ''))}")
                        if doc.get("extracted_fields"):
                            with st.expander("Extracted fields"):
                                st.json(doc["extracted_fields"])
            else:
                st.info("No documents mapped to this workflow yet.")

            # Upload document for this workflow
            st.write("")
            uploaded = st.file_uploader(
                "Upload document for this workflow",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"vs_fco_upload_{wf_id}",
            )
            if uploaded:
                category = st.selectbox(
                    "Document category",
                    options=["death_certificate", "policy_schedule", "claimant_identity", "nominee_proof",
                             "bank_proof", "hospital_bills", "discharge_summary", "prescriptions",
                             "post_mortem", "fir_report", "accident_report", "medical_records",
                             "assignment_docs", "loan_statement", "guardian_certificate", "driving_license",
                             "rc_book", "other"],
                    key=f"vs_fco_cat_{wf_id}",
                )
                if st.button("Add to common index and map to this workflow", key=f"vs_fco_add_doc_{wf_id}"):
                    # Add to common index
                    doc_id = add_common_document(
                        st.session_state,
                        batch.batch_id,
                        category,
                        uploaded.name,
                        uploaded.type or "application/octet-stream",
                        {},  # extracted_fields would come from Sarvam Document AI
                    )
                    # Map to this workflow
                    map_document_to_workflow(st.session_state, doc_id, wf_id)
                    st.success("Document added and mapped.")
                    st.rerun()

            # Timeline
            st.divider()
            st.markdown("### Timeline & status")

            for event in wf.timeline:
                with st.container(border=True):
                    cols = st.columns([2, 1, 3])
                    with cols[0]:
                        st.write(f"**{esc(event.get('event_type', ''))}**")
                        st.caption(f"Date: {esc(event.get('event_date', ''))}")
                    with cols[1]:
                        source = event.get("source", "USER_REPORTED")
                        st.caption(f"Source: {esc(source)}")
                    with cols[2]:
                        st.write(esc(event.get("note", "")))

            # Add timeline event
            st.write("")
            new_event_type = st.selectbox(
                "Add timeline event",
                options=["Document submitted", "Insurer acknowledgement", "Document request received",
                         "Draft sent", "Follow-up made", "User marked submitted", "User marked resolved",
                         "Insurer query recorded", "Other"],
                key=f"vs_fco_new_evt_type_{wf_id}",
            )
            new_event_date = st.date_input("Event date", value=date.today(), key=f"vs_fco_new_evt_date_{wf_id}")
            new_event_note = st.text_area("Note", key=f"vs_fco_new_evt_note_{wf_id}")
            if st.button("Add timeline event", key=f"vs_fco_add_evt_{wf_id}"):
                add_workflow_timeline_event(
                    st.session_state, wf_id, new_event_type, new_event_date, new_event_note
                )
                st.rerun()

            # Draft
            st.divider()
            st.markdown("### Draft communication")
            draft = st.text_area(
                "Editable draft (not sent automatically)",
                value=wf.draft_text,
                height=200,
                key=f"vs_fco_draft_{wf_id}",
            )
            if st.button("Save draft", key=f"vs_fco_save_draft_{wf_id}"):
                save_workflow_draft(st.session_state, wf_id, draft)
                st.success("Draft saved.")

            # Status update
            st.divider()
            st.markdown("### Update workflow status")
            new_status = st.selectbox(
                "New status",
                options=list(WorkflowState.__args__ if hasattr(WorkflowState, '__args__') else [
                    "DISCOVERED", "RELEVANCE_REVIEW", "CHECKLIST_READY", "DOCUMENTS_IN_PROGRESS",
                    "READY_FOR_USER_REVIEW", "DRAFT_PREPARED", "USER_MARKED_SUBMITTED",
                    "FOLLOW_UP", "USER_MARKED_RESOLVED", "INSURER_QUERY_RECORDED",
                ]),
                index=list(WorkflowState.__args__ if hasattr(WorkflowState, '__args__') else [
                    "DISCOVERED", "RELEVANCE_REVIEW", "CHECKLIST_READY", "DOCUMENTS_IN_PROGRESS",
                    "READY_FOR_USER_REVIEW", "DRAFT_PREPARED", "USER_MARKED_SUBMITTED",
                    "FOLLOW_UP", "USER_MARKED_RESOLVED", "INSURER_QUERY_RECORDED",
                ]).index(wf.status) if wf.status in (WorkflowState.__args__ if hasattr(WorkflowState, '__args__') else []) else 0,
                key=f"vs_fco_status_{wf_id}",
            )
            if st.button("Update status", key=f"vs_fco_update_status_{wf_id}"):
                update_workflow_status(st.session_state, wf_id, new_status)
                st.success(f"Status updated to {new_status}")
                st.rerun()

            # Sarvam explanation
            if playbook:
                st.divider()
                st.markdown("### AI next-steps explanation (Sarvam-105B)")
                st.caption(
                    "Sarvam-105B explains the deterministic rule outputs and checklist items. "
                    "It does not decide coverage, eligibility, or claim approval. "
                    "Click the button to generate an explanation. If Sarvam is unavailable, a deterministic fallback is shown."
                )
                from src.sarvam_service import SarvamConfig, SarvamService
                config = SarvamConfig.from_env()
                if not config.is_configured:
                    st.info("Sarvam-105B not configured. Deterministic playbook explanation:")
                    st.write(f"**Policy type:** {esc(policy.get('product_type', 'unknown') if policy else 'unknown')}")
                    st.write(f"**Event relevance:** {esc(EVENT_RELEVANCE_LABELS.get(wf.event_relevance, wf.event_relevance))}")
                    st.write(f"**Next steps:** Complete the checklist above, gather required documents, "
                             f"and contact the insurer ({esc(policy.get('insurer_name', 'N/A') if policy else 'N/A')}) "
                             f"to confirm the exact process and forms.")
                else:
                    if st.button("Generate AI explanation", key=f"vs_fco_ai_explain_{wf_id}", type="primary", width="stretch"):
                        service = SarvamService(config)
                        # Load all workflows and playbooks for context
                        workflows = get_workflows(st.session_state)
                        batch_id = wf.batch_id
                        batches = get_batches(st.session_state)
                        batch = next((b for b in batches if b.batch_id == batch_id), None)
                        child_workflows = [w for w in workflows if w.batch_id == batch_id]
                        playbooks = {}
                        for cw in child_workflows:
                            pb = load_playbook(cw.playbook_id)
                            if pb:
                                playbooks[cw.policy_id] = pb
                        language_name = "English"
                        try:
                            result = service.explain_claim_orchestrator_plan(
                                "en",
                                batch.to_dict() if batch else {"batch_id": batch_id},
                                [cw.to_dict() for cw in child_workflows],
                                playbooks,
                                language_name,
                            )
                            st.session_state[f"vs_fco_ai_result_{wf_id}"] = result.text
                            st.session_state[f"vs_fco_ai_status_{wf_id}"] = result.status
                            st.session_state[f"vs_fco_ai_elapsed_{wf_id}"] = result.elapsed_ms
                        except Exception as e:
                            st.session_state[f"vs_fco_ai_error_{wf_id}"] = str(e)

                    # Display result if available
                    result_key = f"vs_fco_ai_result_{wf_id}"
                    if result_key in st.session_state:
                        status = st.session_state.get(f"vs_fco_ai_status_{wf_id}", "unknown")
                        elapsed = st.session_state.get(f"vs_fco_ai_elapsed_{wf_id}", 0)
                        if status == "success":
                            st.success(f"AI explanation generated ({elapsed} ms)")
                        elif status == "fallback":
                            st.warning(f"AI unavailable, showing fallback ({elapsed} ms)")
                        else:
                            st.info(f"Status: {status}")

                        try:
                            ai_data = json.loads(st.session_state[result_key])
                            st.markdown(f"**Portfolio summary:** {ai_data.get('portfolio_summary', '')}")
                            for exp in ai_data.get("workflow_explanations", []):
                                with st.expander(f"Workflow: {exp.get('workflow_id', '')}"):
                                    st.write(f"**Explanation:** {exp.get('plain_language_explanation', '')}")
                                    st.write(f"**What to verify:** {exp.get('what_to_verify', '')}")
                                    st.caption(f"Sources: {', '.join(exp.get('source_ids', []))}")
                            st.markdown(f"**Portfolio note:** {ai_data.get('portfolio_note', '')}")
                        except json.JSONDecodeError:
                            st.error("Failed to parse AI response")
                            st.code(st.session_state[result_key])

                    error_key = f"vs_fco_ai_error_{wf_id}"
                    if error_key in st.session_state:
                        st.error(f"AI error: {st.session_state[error_key]}")
                        st.write(f"**Policy type:** {esc(policy.get('product_type', 'unknown') if policy else 'unknown')}")
                        st.write(f"**Event relevance:** {esc(EVENT_RELEVANCE_LABELS.get(wf.event_relevance, wf.event_relevance))}")
                        st.write(f"**Next steps:** Complete the checklist above, gather required documents, "
                                 f"and contact the insurer ({esc(policy.get('insurer_name', 'N/A') if policy else 'N/A')}) "
                                 f"to confirm the exact process and forms.")
                    elif result_key not in st.session_state:
                        st.info("Click the button above to generate an AI explanation.")
                        st.write(f"**Policy type:** {esc(policy.get('product_type', 'unknown') if policy else 'unknown')}")
                        st.write(f"**Event relevance:** {esc(EVENT_RELEVANCE_LABELS.get(wf.event_relevance, wf.event_relevance))}")
                        st.write(f"**Next steps:** Complete the checklist above, gather required documents, "
                                 f"and contact the insurer ({esc(policy.get('insurer_name', 'N/A') if policy else 'N/A')}) "
                                 f"to confirm the exact process and forms.")


__all__ = ["render_family_claim_orchestrator"]