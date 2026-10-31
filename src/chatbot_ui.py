"""AI Assistant chatbot UI using Nemotron 3 Ultra via OpenRouter."""

from __future__ import annotations

import html
import json
import os
import time
from typing import Any

import streamlit as st

from src.insurance_inventory import seeded_paytm_records
from src.mock_paytm_data import demo_user_by_id
from src.nominee_consistency import analyse_portfolio, load_linked_profiles
from src.sarvam_service import SarvamConfig

# Import SarvamService dynamically to access LLM methods
from src.sarvam_service import SarvamService

CHATBOT_NOTICE = (
    "This AI assistant uses Nemotron 3 Ultra via OpenRouter. It can answer questions "
    "about your policies, nominee findings, and general insurance concepts. "
    "It does not have access to live insurer data and cannot make legal determinations. "
    "Always verify critical information with your insurer."
)

# System prompt for the insurance assistant
CHATBOT_SYSTEM_PROMPT = (
    "You are an AI assistant for Virasat Saathi, an independent hackathon prototype "
    "for insurance portfolio analysis. You help users understand their policies, "
    "nominee consistency findings, and general insurance concepts. "
    "\n\n"
    "Guidelines:\n"
    "- You are an assistant, not an insurer, lawyer, or financial advisor.\n"
    "- Do not make legal determinations, eligibility decisions, or claim approvals.\n"
    "- Always clarify that you are an AI assistant and not a substitute for professional advice.\n"
    "- Encourage users to verify critical information with their insurer.\n"
    "- You can explain nominee findings, policy terms, claim processes, and insurance concepts.\n"
    "- If asked about specific policy details, only use information provided in context.\n"
    "- Be concise but helpful. Use plain language."
)

# Context injection prompt template
CONTEXT_PROMPT_TEMPLATE = (
    "Current user context:\n"
    "User: {user_name} ({user_id})\n"
    "Policies: {policy_count} policies\n"
    "Policy details:\n{policy_details}\n"
    "Nominee findings: {finding_count} findings\n"
    "Finding summary: {finding_summary}\n\n"
    "User question: {user_question}\n\n"
    "Answer based on the context above. If the question is outside the provided context, "
    "say so and offer general insurance guidance."
)


def _build_policy_context(user_demo_user_id: str) -> tuple[str, int, int, str]:
    """Build context string from user's policies and nominee findings."""
    policies = seeded_paytm_records()
    user_policies = [p for p in policies if p.get("owner_demo_user_id") == user_demo_user_id]

    policy_lines = []
    for p in user_policies:
        policy_lines.append(
            f"  - {p.get('product_name', 'Unknown')} ({p.get('product_type', 'unknown')}) "
            f"| Insurer: {p.get('insurer_name', 'N/A')} "
            f"| Masked ID: {p.get('policy_number_masked', 'N/A')} "
            f"| Period: {p.get('policy_start_date', 'N/A')} to {p.get('policy_end_date', 'N/A')} "
            f"| Nominee: {p.get('ocr_nominee_name') or p.get('policyholder_name', 'Not in record')} "
            f"| Status: {p.get('verification_status', 'N/A')}"
        )

    # Try to get nominee findings
    finding_count = 0
    finding_summary = "No analysis run yet"
    try:
        linked_profiles = __import__('src.nominee_consistency', fromlist=['load_linked_profiles']).load_linked_profiles()
        from src.insurance_ui import _active_user
        from src.mock_paytm_data import users_as_dicts
        users = users_as_dicts()
        owner = _active_user(users)
        links = []  # Simplified - would need session state for real links
        findings, summary = analyse_portfolio(
            owner_demo_user_id=user_demo_user_id,
            event_date=__import__('datetime').date.today(),
            linked_profiles=linked_profiles,
            nominee_links=links,
        )
        finding_count = len(findings)
        if findings:
            codes = {}
            for f in findings:
                codes[f.finding_code] = codes.get(f.finding_code, 0) + 1
            finding_summary = ", ".join(f"{k}: {v}" for k, v in codes.items())
    except Exception:
        pass

    return (
        "\n".join(policy_lines),
        len(user_policies),
        finding_count,
        finding_summary,
    )


def _call_nemotron(messages: list[dict[str, str]]) -> str:
    """Call Nemotron 3 Ultra via OpenRouter."""
    model = os.environ.get("LLM_105B_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    timeout = float(os.environ.get("LLM_105B_TIMEOUT_SECONDS", "15"))
    max_tokens = int(os.environ.get("LLM_105B_MAX_OUTPUT_TOKENS", "2000"))
    base_url = os.environ.get("LLM_105B_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.environ.get("LLM_105B_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))

    if not api_key:
        raise ValueError("LLM_105B_API_KEY or OPENROUTER_API_KEY not configured")

    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=0,
    )

    response = client.chat.completions.create(
        model=os.environ.get("LLM_105B_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"),
        messages=messages,
        temperature=0.3,
        max_tokens=int(os.environ.get("LLM_105B_MAX_OUTPUT_TOKENS", "2000")),
        timeout=timeout,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("provider returned empty text")
    return content.strip()


def render_chatbot(user_demo_user_id: str) -> None:
    """Render the AI Assistant chatbot interface."""
    st.markdown("## AI Assistant — Nemotron 3 Ultra")
    st.info(CHATBOT_NOTICE)
    st.divider()

    # Build context
    policy_details, policy_count, finding_count, finding_summary = _build_policy_context(user_demo_user_id)

    # Initialize chat history
    if "vs_chatbot_messages" not in st.session_state:
        st.session_state["vs_chatbot_messages"] = [
            {"role": "assistant", "content": (
                "Hello! I'm your AI assistant powered by Nemotron 3 Ultra. "
                "I can help you with:\n"
                "- Explaining your policy details and coverage\n"
                "- Interpreting nominee consistency findings\n"
                "- Explaining claim processes and required documents\n"
                "- General insurance concepts and terminology\n\n"
                f"You have **{policy_count} policies** in your portfolio. "
                f"Run Nominee 360 analysis to see **{finding_count} findings** ({finding_summary}).\n\n"
                "What would you like to know?"
            )}
        ]

    # Display chat history
    for msg in st.session_state["vs_chatbot_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your policies, nominee findings, or insurance...", key="vs_chatbot_input"):
        # Add user message
        st.session_state["vs_chatbot_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Build context-aware messages
                    messages = [
                        {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
                        {"role": "user", "content": CONTEXT_PROMPT_TEMPLATE.format(
                            user_name=demo_user_by_id(user_demo_user_id).get("display_name", "User"),
                            user_id=user_demo_user_id,
                            policy_count=policy_count,
                            policy_details=policy_details,
                            finding_count=finding_count,
                            finding_summary=finding_summary,
                            user_question=prompt,
                        )},
                    ]

                    # Add recent chat history (last 6 messages)
                    for msg in st.session_state["vs_chatbot_messages"][-6:]:
                        if msg["role"] in ("user", "assistant"):
                            messages.append({"role": msg["role"], "content": msg["content"]})

                    response = _call_nemotron(messages)
                    st.markdown(response)
                    st.session_state["vs_chatbot_messages"].append({"role": "assistant", "content": response})

                except Exception as e:
                    error_msg = f"Error: {str(e)[:200]}"
                    st.error(error_msg)
                    st.session_state["vs_chatbot_messages"].append({"role": "assistant", "content": error_msg})

    # Sidebar controls
    with st.sidebar:
        st.markdown("### Chat Controls")
        if st.button("Clear chat history", key="vs_chatbot_clear", width="stretch"):
            st.session_state["vs_chatbot_messages"] = [
                {"role": "assistant", "content": (
                    "Hello! I'm your AI assistant powered by Nemotron 3 Ultra. "
                    "I can help you with:\n"
                    "- Explaining your policy details and coverage\n"
                    "- Interpreting nominee consistency findings\n"
                    "- Explaining claim processes and required documents\n"
                    "- General insurance concepts and terminology\n\n"
                    f"You have **{policy_count} policies** in your portfolio. "
                    f"Run Nominee 360 analysis to see **{finding_count} findings** ({finding_summary}).\n\n"
                    "What would you like to know?"
                )}
            ]
            st.rerun()

        # Show API status
        st.markdown("### API Status")
        config = SarvamConfig.from_env()
        if config.is_configured:
            st.success("Sarvam configured")
        else:
            st.warning("Sarvam not configured")

        # Check OpenRouter key
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", os.environ.get("LLM_105B_API_KEY", ""))
        if openrouter_key and openrouter_key != "your_openrouter_key_here":
            st.success("OpenRouter key configured")
        else:
            st.warning("OpenRouter key not set - using fallback")


__all__ = ["render_chatbot"]