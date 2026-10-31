"""Virasat Saathi — independent hackathon prototype.

Run locally with:
    streamlit run app.py

The app is synthetic-data-first and works without Sarvam or any network access.
It has no live banking, insurer, UPI-mandate or government-portal integration.
"""

from __future__ import annotations

import html
import logging
from datetime import date

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.claims_engine import (  # noqa: E402
    answer_policy_topic,
    case_summary_text,
    checklist_progress,
    checklist_status,
    validate_claim_against_policy,
)
from src.document_parser import (  # noqa: E402
    UploadError,
    extract_pdf_text_in_memory,
    extract_text_in_memory,
    parse_transactions_csv,
    validate_upload,
)
from src.draft_templates import (  # noqa: E402
    DRAFT_KIND_KEYS,
    draft_kind_label,
    generate_draft,
)
from src.fixtures import (  # noqa: E402
    load_claim,
    load_demo_transactions_bytes,
    load_policy,
    load_source_registry,
)
from src.insurance_ui import render_active_insurances  # noqa: E402
from src.mock_auth import authenticate, login_id_for_user, preset_accounts  # noqa: E402
from src.mock_paytm_data import demo_user_by_id  # noqa: E402
from src.models import DemoClaim, Language  # noqa: E402
from src.safety import format_inr  # noqa: E402
from src.sarvam_service import (  # noqa: E402
    ALLOWED_MISSING_CATEGORIES,
    FIXED_SOURCE_EXCERPTS,
    SarvamConfig,
    SarvamService,
    deterministic_explanation,
)
from src.transaction_matcher import (  # noqa: E402
    category_label,
    match_transactions,
)
from src.translations import t, topic_label  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)

st.set_page_config(
    page_title="Virasat Saathi — Independent hackathon prototype",
    page_icon="🪔",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_SESSION = {
    "vs_page": "home",
    "vs_language_choice": "en",
    "vs_auth_user_id": None,
    "vs_login_error": "",
    "vs_claim_loaded": False,
    "vs_family_loaded": False,
    "vs_family_mode": "demo",
    "vs_sarvam_opt_in": False,
    "vs_insurance_active_user_id": "paytm.demo.aarav",
    "vs_insurance_section": "bought",
    "vs_insurance_upload_nonce": 0,
    "vs_insurance_nominee_policy_id": None,
    "vs_insurance_review_policy_id": None,
}

CLAIM_SCRATCH_PREFIXES = (
    "vs_provided_",
    "vs_step_",
    "vs_draft_",
    "vs_sarvam_result",
    "vs_sarvam_category",
    "vs_doc_",
    "vs_claim_doc_present",
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pill(text: str, css_class: str = "vs-pill-neutral") -> str:
    return f'<span class="vs-pill {css_class}">{esc(text)}</span>'


def note(text: str, warning: bool = False) -> str:
    css = "vs-warning" if warning else "vs-note"
    return f'<div class="{css}">{esc(text)}</div>'


def init_session() -> None:
    for key, value in DEFAULT_SESSION.items():
        if key not in st.session_state:
            st.session_state[key] = value


def current_auth_user() -> dict[str, object] | None:
    """Return the signed-in fixture user, or ``None`` when logged out."""
    user_id = st.session_state.get("vs_auth_user_id")
    if not user_id:
        return None
    user = demo_user_by_id(str(user_id))
    if user is None:
        st.session_state["vs_auth_user_id"] = None
    return user


def login_account(demo_user_id: str) -> None:
    """Start a local fixture session for one seeded user."""
    st.session_state["vs_auth_user_id"] = demo_user_id
    st.session_state["vs_insurance_active_user_id"] = demo_user_id
    st.session_state["vs_insurance_nominee_policy_id"] = None
    st.session_state["vs_insurance_review_policy_id"] = None
    st.session_state["vs_page"] = "home"
    st.session_state["vs_login_error"] = ""
    st.session_state.pop("vs_login_password", None)


def logout_account() -> None:
    """End the local session without deleting session policy records."""
    st.session_state["vs_auth_user_id"] = None
    st.session_state["vs_insurance_active_user_id"] = None
    st.session_state["vs_insurance_nominee_policy_id"] = None
    st.session_state["vs_insurance_review_policy_id"] = None
    st.session_state["vs_page"] = "home"
    st.session_state["vs_login_error"] = ""
    st.session_state.pop("vs_login_password", None)


def try_login(login_id: object, password: object) -> bool:
    demo_user_id = authenticate(login_id, password)
    if demo_user_id is None:
        st.session_state["vs_login_error"] = (
            "That login ID or password does not match a preset account."
        )
        return False
    login_account(demo_user_id)
    return True


def _drop_prefixes(prefixes: tuple[str, ...]) -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and any(key.startswith(prefix) for prefix in prefixes):
            del st.session_state[key]


def load_demo_claim_state() -> None:
    _drop_prefixes(CLAIM_SCRATCH_PREFIXES)
    st.session_state["vs_claim_loaded"] = True
    st.session_state["vs_page"] = "claims"


def clear_checklist_state() -> None:
    for item in load_claim().required_document_categories:
        st.session_state.pop(f"vs_provided_{item.id}", None)


def load_family_state() -> None:
    _drop_prefixes(
        (
            "vs_family_upload",
            "vs_family_ack",
            "vs_family_note",
            "vs_family_step_",
            "vs_family_upload_present",
        )
    )
    st.session_state["vs_family_loaded"] = True
    st.session_state["vs_family_mode"] = "demo"
    st.session_state["vs_page"] = "family"


def current_provided_ids(claim: DemoClaim) -> set[str]:
    return {
        item.id
        for item in claim.required_document_categories
        if st.session_state.get(f"vs_provided_{item.id}", False)
    }


def current_tracker_state(claim: DemoClaim) -> dict[str, dict[str, object]]:
    return {
        step.id: {
            "done": bool(st.session_state.get(f"vs_step_done_{step.id}", False)),
            "due": st.session_state.get(f"vs_step_due_{step.id}", ""),
            "notes": st.session_state.get(f"vs_step_notes_{step.id}", ""),
        }
        for step in claim.timeline
    }


def status_label(status: str, language: Language) -> str:
    return t(f"status_{status}", language)


def status_class(status: str) -> str:
    if status == "marked_provided":
        return "vs-pill-info"
    if status == "needs_confirmation":
        return "vs-pill-demo"
    return "vs-pill-neutral"


def render_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --vs-navy: #12355B;
            --vs-teal: #0F766E;
            --vs-saffron: #C47A12;
            --vs-bg: #F7F5F0;
            --vs-ink: #1B2A38;
            --vs-muted: #5B6B7A;
            --vs-border: #E6E0D4;
        }
        .stApp {
            background: radial-gradient(circle at top left, #FBF8F1 0, #F7F5F0 42%, #F4F2EC 100%);
            color: var(--vs-ink);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1.1rem;
            padding-bottom: 3rem;
        }
        header[data-testid="stHeader"] { background: transparent; }
        h1, h2, h3, h4 { color: var(--vs-navy); }
        a { color: var(--vs-teal); }
        .vs-header { display: flex; align-items: center; gap: 14px; }
        .vs-title {
            font-size: 1.55rem; font-weight: 800; color: var(--vs-navy);
            line-height: 1.05; letter-spacing: -0.03em;
        }
        .vs-tagline { color: var(--vs-muted); font-size: .86rem; margin-top: 4px; }
        .vs-mini {
            font-size: .72rem; color: var(--vs-teal); font-weight: 700;
            letter-spacing: .06em; text-transform: uppercase; margin-top: 6px;
        }
        .vs-banner {
            background: #FFF8E8; border: 1px solid #EBCF9A; color: #5C430F;
            padding: 12px 16px; border-radius: 14px; font-size: .92rem;
            margin: 18px 0 10px; line-height: 1.5;
        }
        .vs-card {
            background: rgba(255,255,255,.94); border: 1px solid var(--vs-border);
            border-radius: 20px; padding: 22px 22px 18px;
            box-shadow: 0 10px 30px rgba(18,53,91,.05); height: 100%;
        }
        .vs-card h3 { margin: 8px 0 6px; font-size: 1.25rem; }
        .vs-card p { color: var(--vs-muted); line-height: 1.55; margin: 0; }
        .vs-kicker {
            color: var(--vs-teal); font-size: .72rem; letter-spacing: .14em;
            text-transform: uppercase; font-weight: 800;
        }
        .vs-pill {
            display: inline-block; padding: 4px 10px; border-radius: 999px;
            font-size: .74rem; font-weight: 700; letter-spacing: .01em;
            margin: 2px 4px 2px 0;
        }
        .vs-pill-demo { background: #FDF1D6; color: #7A5200; }
        .vs-pill-info { background: #E6F3F1; color: #0B5C55; }
        .vs-pill-neutral { background: #EDF1F5; color: #3A4A5A; }
        .vs-pill-ai { background: #EDE9FE; color: #4C1D95; }
        .vs-note {
            background: #F4F8F7; border: 1px solid #CFE5E1; border-left: 4px solid var(--vs-teal);
            border-radius: 12px; padding: 12px 14px; color: #25413F;
            font-size: .9rem; line-height: 1.5;
        }
        .vs-warning {
            background: #FFF7E8; border: 1px solid #EBCF9A; border-left: 4px solid var(--vs-saffron);
            border-radius: 12px; padding: 12px 14px; color: #5C430F;
            font-size: .9rem; line-height: 1.5;
        }
        .vs-evidence {
            background: #FAFCFB; border: 1px solid #DCEBE8;
            border-left: 3px solid var(--vs-teal); border-radius: 0 12px 12px 0;
            padding: 9px 12px; margin: 7px 0; font-size: .88rem;
        }
        .vs-mono {
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            color: #506274; font-size: .78rem;
        }
        .vs-footer {
            border-top: 1px solid var(--vs-border); margin-top: 34px;
            padding-top: 16px; color: var(--vs-muted); font-size: .8rem;
            line-height: 1.6;
        }
        div.stButton > button {
            border-radius: 999px; border: 1px solid #CBD5DF;
            padding: .52rem 1rem; font-weight: 650;
        }
        div.stButton > button[kind="primary"] {
            background: var(--vs-navy); border-color: var(--vs-navy); color: #fff;
        }
        div.stButton > button[kind="primary"]:hover {
            background: #0B2745; border-color: #0B2745; color: #fff;
        }
        div.stDownloadButton > button { border-radius: 999px; }
        [data-testid="stMetricValue"] { color: var(--vs-navy); font-weight: 800; }
        [data-testid="stMetricLabel"] { color: var(--vs-muted); }
        hr { border-color: var(--vs-border); }
        .vs-paytm-strip {
            background: linear-gradient(90deg, #E8F1FF 0%, #F4F8FF 55%, #EAF6F3 100%);
            border: 1px solid #BBD4F7; color: #0B3B8C;
            border-radius: 14px; padding: 10px 14px;
            font-size: .86rem; font-weight: 700; line-height: 1.45;
            margin: 12px 0 16px;
        }
        .vs-session-card {
            display: flex; align-items: center; gap: 14px;
            background: #F3F8FF; border: 1px solid #C9DDF7;
            border-radius: 18px; padding: 14px 16px; margin: 8px 0 4px;
        }
        .vs-session-avatar {
            width: 46px; height: 46px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: #0B3B8C; color: #fff; font-weight: 800;
            letter-spacing: .02em;
        }
        .vs-session-name { color: #0B3B8C; font-weight: 800; font-size: 1.02rem; }
        .vs-insurer-name {
            color: #0B3B8C; font-weight: 800; font-size: 1.1rem;
            letter-spacing: -0.01em; margin-bottom: 4px;
        }
        .vs-fact-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
            gap: 10px 16px; background: #F8FBFF; border: 1px solid #E1ECFA;
            border-radius: 14px; padding: 12px 14px; margin: 10px 0;
        }
        .vs-fact-grid div { min-width: 0; }
        .vs-fact-label {
            display: block; color: #5B6B7A; font-size: .72rem;
            text-transform: uppercase; letter-spacing: .06em; font-weight: 700;
            margin-bottom: 2px;
        }
        .vs-fact-grid strong {
            display: block; color: #1B2A38; font-size: .92rem;
            font-weight: 700; overflow-wrap: anywhere;
        }
        .vs-pill-paytm { background: #E6F0FF; color: #0B3B8C; }
        .vs-pill-review { background: #FFF1D6; color: #7A5200; }
        .vs-pill-shared { background: #E6F7EE; color: #0B6B3A; }
        .vs-profile-card {
            display: flex; align-items: center; gap: 10px;
            background: #F3F8FF; border: 1px solid #C9DDF7;
            border-radius: 18px; padding: 8px 12px;
        }
        .vs-profile-avatar {
            width: 40px; height: 40px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #00BAF2, #0B3B8C);
            color: #fff; font-weight: 800; font-size: .86rem;
            letter-spacing: .02em; flex: 0 0 auto;
        }
        .vs-profile-name {
            color: #0B3B8C; font-weight: 800; font-size: .92rem;
            line-height: 1.1;
        }
        .vs-profile-id {
            color: #5B6B7A; font-size: .72rem; margin-top: 2px;
        }
        .vs-login-hero {
            background: linear-gradient(145deg, #002970 0%, #0B4FA8 55%, #00BAF2 100%);
            border-radius: 26px; padding: 42px 38px; color: #fff;
            min-height: 420px; box-shadow: 0 20px 45px rgba(0,41,112,.18);
        }
        .vs-login-hero h1 {
            color: #fff; font-size: 2.2rem; line-height: 1.12;
            letter-spacing: -0.04em; margin: 18px 0 14px;
        }
        .vs-login-hero p { color: #DCEBFF; font-size: 1rem; line-height: 1.6; }
        .vs-login-hero ul {
            margin: 22px 0 0; padding-left: 18px; color: #EAF4FF;
            line-height: 1.9; font-size: .92rem;
        }
        .vs-login-badge {
            display: inline-block; background: rgba(255,255,255,.16);
            border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
            padding: 6px 12px; font-size: .7rem; font-weight: 800;
            letter-spacing: .12em; text-transform: uppercase;
        }
        .vs-login-brand { font-size: 1.15rem; font-weight: 800; letter-spacing: .01em; }
        .vs-login-title {
            color: #002970; font-size: 1.55rem; font-weight: 800;
            letter-spacing: -0.03em; margin-bottom: 4px;
        }
        .vs-login-copy { color: #5B6B7A; font-size: .9rem; margin-bottom: 14px; }
        .vs-login-footer {
            color: #5B6B7A; font-size: .78rem; line-height: 1.55;
            margin-top: 18px; text-align: center;
        }
        .vs-account-line {
            background: #F3F8FF; border: 1px solid #D8E6FA;
            border-radius: 12px; padding: 10px 12px; margin: 8px 0;
        }
        .vs-account-line strong { color: #002970; }
        @media (max-width: 760px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .vs-title { font-size: 1.3rem; }
            .vs-fact-grid { grid-template-columns: 1fr 1fr; gap: 8px 10px; }
            .vs-session-card { align-items: flex-start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_profile(user: dict[str, object]) -> None:
    demo_user_id = str(user.get("demo_user_id", ""))
    login_id = login_id_for_user(demo_user_id) or "account"
    st.markdown(
        f"""
        <div class="vs-profile-card">
          <div class="vs-profile-avatar">{esc(user.get('initials', 'VS'))}</div>
          <div>
            <div class="vs-profile-name">{esc(user.get('display_name', 'Signed in'))}</div>
            <div class="vs-profile-id">@{esc(login_id)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "Log out",
        key="vs_logout",
        width="stretch",
    ):
        logout_account()
        st.rerun()


def render_header() -> Language:
    init_session()
    language: Language = st.session_state.get("vs_language_choice", "en")  # type: ignore[assignment]
    left, right = st.columns([0.72, 0.28])
    with left:
        st.markdown(
            f"""
            <div class="vs-header">
              <svg width="46" height="46" viewBox="0 0 46 46" aria-hidden="true">
                <rect x="2" y="2" width="42" height="42" rx="14" fill="#12355B"/>
                <path d="M12 29c8-1 12-6 13-14 5 6 4 13-2 17-4 3-9 2-11-3z" fill="#7DD3C7"/>
                <circle cx="32" cy="14" r="3" fill="#E9A23B"/>
              </svg>
              <div>
                <div class="vs-title">{esc(t('app_title', language))}</div>
                <div class="vs-tagline">{esc(t('app_tagline', language))}</div>
                <div class="vs-mini">{esc(t('prototype_label', language))}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        user = current_auth_user()
        if user is not None:
            render_profile(user)
    return "en"


def render_login() -> None:
    """Render the local, preset-credential sign-in screen."""
    init_session()
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="vs-login-hero">
              <div class="vs-login-brand">Virasat Saathi</div>
              <div class="vs-login-badge">Paytm-style experience</div>
              <h1>All your insurance,<br/>in one calm place.</h1>
              <p>
                Sign in to see the policies linked to your account, open policy
                documents, upload an external policy for extraction, and manage
                family-sharing requests.
              </p>
              <ul>
                <li>Policies bought on Paytm in one inventory</li>
                <li>Document viewer for every policy</li>
                <li>Explicitly consented nominee summaries</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="vs-login-title">Log in</div>'
                '<div class="vs-login-copy">Use one of the preset prototype accounts.</div>',
                unsafe_allow_html=True,
            )
            login_id = st.text_input(
                "Login ID",
                key="vs_login_id",
                placeholder="aarav",
            )
            password = st.text_input(
                "Password",
                type="password",
                key="vs_login_password",
                placeholder="Enter preset password",
            )
            if st.button(
                "Log in",
                key="vs_login_submit",
                type="primary",
                width="stretch",
            ):
                if try_login(login_id, password):
                    st.rerun()
            error = str(st.session_state.get("vs_login_error", ""))
            if error:
                st.error(error)
            st.caption(
                "Prototype sign-in only. Accounts are local fixtures; this is not "
                "Paytm authentication. No OTP, UPI PIN or real credential is used."
            )

        with st.expander("Preview access details"):
            for account in preset_accounts():
                st.markdown(
                    f"""
                    <div class="vs-account-line">
                      <strong>{esc(account['display_name'])}</strong><br/>
                      Login ID: <code>{esc(account['login_id'])}</code> ·
                      Password: <code>{esc(account['password'])}</code>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.caption(
                "These are deliberate local test credentials for the independent "
                "prototype, not Paytm or insurer credentials."
            )

    st.markdown(
        '<div class="vs-login-footer">'
        "Independent hackathon prototype. Not affiliated with Paytm, any insurer "
        "or Sarvam AI. Use synthetic records only."
        "</div>",
        unsafe_allow_html=True,
    )


def render_privacy_banner(language: Language) -> None:
    st.markdown(
        f'<div class="vs-banner" role="note">{esc(t("privacy_banner", language))}</div>',
        unsafe_allow_html=True,
    )


def render_top_nav(language: Language) -> None:
    """Compact navigation shared by the Phase 1 and Phase 2 journeys."""
    current = str(st.session_state.get("vs_page", "home"))
    items = [
        ("home", "Home", "vs_nav_home"),
        ("claims", "Claims Companion", "vs_nav_claims"),
        ("family", "Family Finance Finder", "vs_nav_family"),
        ("insurance", "Active Insurances", "vs_nav_insurance"),
    ]
    columns = st.columns(len(items))
    for column, (target, label, key) in zip(columns, items):
        with column:
            if st.button(
                label,
                key=key,
                type="primary" if current == target else "secondary",
                width="stretch",
            ):
                st.session_state["vs_page"] = target
                st.rerun()


def render_journey_card(
    kicker: str, title: str, description: str, icon: str
) -> None:
    st.markdown(
        f"""
        <div class="vs-card">
          <div style="font-size:1.7rem">{icon}</div>
          <div class="vs-kicker">{esc(kicker)}</div>
          <h3>{esc(title)}</h3>
          <p>{esc(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home(language: Language) -> None:
    st.markdown(f"## {esc(t('home_heading', language))}")
    st.caption(t("home_sub", language))
    st.write("")

    left, right = st.columns(2, gap="large")
    with left:
        render_journey_card(
            t("journey_01", language),
            t("claims_card_title", language),
            t("claims_card_desc", language),
            "🛡️",
        )
        st.write("")
        if st.button(
            t("claims_card_cta", language),
            key="vs_open_claims",
            type="primary",
            width="stretch",
        ):
            st.session_state["vs_page"] = "claims"
            st.rerun()
    with right:
        render_journey_card(
            t("journey_02", language),
            t("family_card_title", language),
            t("family_card_desc", language),
            "🔎",
        )
        st.write("")
        if st.button(
            t("family_card_cta", language),
            key="vs_open_family",
            type="primary",
            width="stretch",
        ):
            st.session_state["vs_page"] = "family"
            st.rerun()

    st.write("")
    render_journey_card(
        "Journey 03 · Insurance inventory",
        "Active Insurances",
        (
            "See your policies, upload an external policy for Sarvam Document AI "
            "extraction, open the policy document, and manage explicitly shared "
            "nominee summaries."
        ),
        "🧾",
    )
    st.write("")
    if st.button(
        "Open Active Insurances",
        key="vs_open_insurance",
        type="primary",
        width="stretch",
    ):
        st.session_state["vs_page"] = "insurance"
        st.rerun()

    st.write("")
    st.markdown(note(t("home_trust_note", language)), unsafe_allow_html=True)
    render_sources_expander(language)


def render_sources_expander(language: Language) -> None:
    registry = load_source_registry()
    with st.expander(t("sources_title", language)):
        st.write(t("sources_sub", language))
        st.markdown(f"**{esc(t('no_portal_queried', language))}**")
        for source in registry.sources:
            st.markdown(f"**[{esc(source.title)}]({source.url})**")
            st.caption(
                f"{source.purpose} · {source.source_type} · "
                f"{t('source_checked_label', language)}: {source.checked_on}"
            )
            st.caption(source.notes)
        st.markdown(f"**{esc(t('limitations_title', language))}**")
        st.write(t("limitations_body", language))


def render_claim_overview(language: Language, claim: DemoClaim) -> None:
    status_text = (
        claim.claim_status_label_hi if language == "hi" else claim.claim_status_label_en
    )
    claimant = claim.claimant_label_hi if language == "hi" else claim.claimant_label
    hospital = claim.hospital_label_hi if language == "hi" else claim.hospital_label
    policy = claim.policy_label_hi if language == "hi" else claim.policy_label
    st.markdown(
        f"""
        <div class="vs-card">
          <div class="vs-kicker">{esc(t('demo_case_label', language))} · {esc(claim.case_id)}</div>
          <h2 style="margin:6px 0 8px;">{esc(t('claim_overview', language))}</h2>
          <div>
            {pill(t('demo_loaded', language), 'vs-pill-demo')}
            {pill(status_text, 'vs-pill-neutral')}
          </div>
          <p style="margin-top:12px;">
            {esc(t('product_label', language))}: {esc(t('claim_type_value', language))}<br/>
            {esc(t('claimant_label', language))}: {esc(claimant)}<br/>
            {esc(t('hospital_label', language))}: {esc(hospital)}<br/>
            {esc(t('policy_label', language))}: {esc(policy)}<br/>
            {esc(t('checklist_source_label', language))}: {esc(claim.checklist_source_id)}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(note(t("claims_disclaimer", language)), unsafe_allow_html=True)


def render_policy_facts(language: Language) -> None:
    policy = load_policy()
    registry = load_source_registry()
    st.subheader(t("policy_facts_title", language))
    st.caption(t("policy_facts_sub", language))

    facts = policy.facts_by_topic()
    topics = list(facts.keys())
    selected = st.selectbox(
        t("policy_lookup_label", language),
        options=[""] + topics,
        format_func=lambda value: t("choose_topic", language)
        if value == ""
        else topic_label(value, language),
        index=1,
        key="vs_policy_topic",
        help=t("policy_lookup_help", language),
    )
    if selected:
        answer = answer_policy_topic(policy, selected)
        statement = answer.statement_hi if language == "hi" else answer.statement_en
        st.markdown(note(statement), unsafe_allow_html=True)
        if answer.verified:
            st.caption(
                f"{t('clause_label', language)}: {answer.clause_id} · "
                f"{t('page_label', language)} {answer.page} · "
                f"{t('synthetic_sample_wording', language)}"
            )
            clause = policy.clause_by_id(answer.clause_id or "")
            if clause is not None:
                with st.expander(t("why_listed", language)):
                    st.write(clause.text)
                    st.caption(
                        f"{clause.id} · {t('page_label', language)} {clause.page}"
                    )
        else:
            st.warning(t("not_verified", language))
            source = registry.by_id("irdai_health_dept")
            if source is not None:
                st.link_button(t("insurer_link_cta", language), source.url)

    with st.expander(t("policy_facts_title", language)):
        for fact in policy.facts:
            statement = fact.statement_hi if language == "hi" else fact.statement_en
            st.markdown(f"**{esc(topic_label(fact.topic, language))}**")
            st.write(statement)
            st.caption(
                f"{fact.clause_id} · {t('page_label', language)} {fact.page} · "
                f"{t('synthetic_sample_wording', language)}"
            )
        st.divider()
        for clause in policy.clauses:
            st.markdown(f"**{esc(clause.heading)}**")
            st.caption(f"{clause.id} · {t('page_label', language)} {clause.page}")
            st.write(clause.text)


def render_checklist(
    language: Language, claim: DemoClaim, provided_ids: set[str]
) -> tuple[set[str], object]:
    st.subheader(t("checklist_title", language))
    st.caption(t("checklist_sub", language))
    st.markdown(note(t("checklist_validation_note", language)), unsafe_allow_html=True)
    st.write("")

    local_provided = set(provided_ids)
    for item in claim.required_document_categories:
        label = item.label_hi if language == "hi" else item.label_en
        why = item.why_hi if language == "hi" else item.why_en
        with st.container(border=True):
            checkbox_col, status_col = st.columns([0.72, 0.28])
            with checkbox_col:
                checked = st.checkbox(label, key=f"vs_provided_{item.id}")
            if checked:
                local_provided.add(item.id)
            else:
                local_provided.discard(item.id)
            status = checklist_status(item, local_provided)
            with status_col:
                st.markdown(
                    pill(status_label(status, language), status_class(status)),
                    unsafe_allow_html=True,
                )
            st.caption(
                f"{t('source_id_label', language)}: {item.source_clause_id} · "
                f"{t('page_label', language)} {item.source_page}"
            )
            with st.expander(t("why_listed", language)):
                st.write(why)
                st.caption(t("synthetic_sample_wording", language))

    progress = checklist_progress(claim, local_provided)
    st.write("")
    first, second, third = st.columns(3)
    first.metric(t("checklist_progress_marked", language), progress.marked)
    second.metric(t("checklist_progress_remaining", language), progress.remaining)
    third.metric(t("checklist_progress_confirm", language), progress.needs_confirmation)
    st.button(
        t("reset_checklist", language),
        key="vs_clear_checklist",
        on_click=clear_checklist_state,
    )
    st.caption(t("checklist_progress_caption", language))
    return local_provided, progress


def render_ai_panel(
    language: Language, claim: DemoClaim, provided_ids: set[str]
) -> None:
    st.subheader(t("sarvam_switch_label", language))
    st.caption(t("sarvam_switch_help", language))

    config = SarvamConfig.from_env()
    service = SarvamService(config)
    st.caption(
        f"{t('sarvam_status_label', language)}: {t(config.status_key, language)}"
    )

    if st.session_state.get("vs_claim_doc_present", False):
        st.info(t("uploaded_doc_ai_disabled", language))
        return

    enabled = st.toggle(
        t("sarvam_switch_label", language),
        key="vs_sarvam_opt_in",
        disabled=not config.is_configured,
        help=t("sarvam_switch_help", language),
    )

    allowed_items = [
        item
        for item in claim.required_document_categories
        if item.id in ALLOWED_MISSING_CATEGORIES
    ]
    options = [item.id for item in allowed_items]
    if not options:
        return
    selected_id = st.selectbox(
        t("sarvam_choose_category", language),
        options=options,
        format_func=lambda value: (
            claim.category_by_id(value).label_hi
            if language == "hi" and claim.category_by_id(value)
            else claim.category_by_id(value).label_en
            if claim.category_by_id(value)
            else value
        ),
        key="vs_sarvam_category",
    )
    selected = claim.category_by_id(selected_id)
    if selected is None:
        return
    source_id = (
        "demo_policy_clause_01"
        if selected.source_clause_id == "demo_policy_clause_01"
        else "demo_checklist_01"
    )

    result_payload: dict[str, object] | None = None
    if not enabled or not config.is_configured:
        result_payload = {
            "text": deterministic_explanation(language, selected_id),  # type: ignore[arg-type]
            "ai_used": False,
            "status": "disabled",
            "note_key": "sarvam_disabled_note",
            "category": selected_id,
            "language": language,
            "source_id": source_id,
        }
    else:
        if st.button(
            t("sarvam_request_button", language),
            key="vs_sarvam_request",
            type="primary",
        ):
            result = service.explain_demo_checklist(
                language=language,
                claim_type="health_reimbursement",
                missing_category=selected_id,  # type: ignore[arg-type]
                source_excerpt_id=source_id,  # type: ignore[arg-type]
            )
            st.session_state["vs_sarvam_result"] = {
                "text": result.text,
                "ai_used": result.ai_used,
                "status": result.status,
                "note_key": result.note_key,
                "category": selected_id,
                "language": language,
                "source_id": source_id,
            }
        stored = st.session_state.get("vs_sarvam_result")
        if (
            isinstance(stored, dict)
            and stored.get("category") == selected_id
            and stored.get("language") == language
        ):
            result_payload = stored
        else:
            st.caption(t("sarvam_not_requested", language))
            result_payload = {
                "text": deterministic_explanation(language, selected_id),  # type: ignore[arg-type]
                "ai_used": False,
                "status": "disabled",
                "note_key": "sarvam_disabled_note",
                "category": selected_id,
                "language": language,
                "source_id": source_id,
            }

    if result_payload is None:
        return
    text = str(result_payload.get("text", ""))
    ai_used = bool(result_payload.get("ai_used", False))
    note_key = str(result_payload.get("note_key", "sarvam_disabled_note"))
    if ai_used:
        st.markdown(
            pill(t("ai_generated_label", language), "vs-pill-ai"),
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="vs-note">{esc(text).replace(chr(10), "<br/>")}</div>',
        unsafe_allow_html=True,
    )
    st.caption(t(note_key, language))
    st.caption(t("sarvam_verify_note", language))
    with st.expander(t("sarvam_source_label", language)):
        st.markdown(f"> {FIXED_SOURCE_EXCERPTS[source_id]}")
        st.caption(
            f"{t('source_id_label', language)}: {source_id} · "
            f"{t('synthetic_sample_wording', language)}"
        )


def render_drafts(
    language: Language,
    claim: DemoClaim,
    policy: object,
    provided_ids: set[str],
) -> None:
    st.subheader(t("draft_title", language))
    st.caption(t("draft_sub", language))
    st.markdown(note(t("draft_no_submission", language), warning=True), unsafe_allow_html=True)
    st.write("")

    kinds = list(DRAFT_KIND_KEYS.keys())
    kind = st.selectbox(
        t("draft_kind_label", language),
        options=kinds,
        format_func=lambda value: draft_kind_label(value, language),
        key="vs_draft_kind",
    )

    missing_id: str | None = None
    if kind in {"missing_document_followup", "additional_information"}:
        category_ids = [item.id for item in claim.required_document_categories]
        first_unmarked = next(
            (
                index
                for index, item in enumerate(claim.required_document_categories)
                if item.id not in provided_ids
            ),
            0,
        )
        missing_id = st.selectbox(
            t("draft_missing_label", language),
            options=category_ids,
            format_func=lambda value: (
                claim.category_by_id(value).label_hi
                if language == "hi" and claim.category_by_id(value)
                else claim.category_by_id(value).label_en
                if claim.category_by_id(value)
                else value
            ),
            index=first_unmarked,
            key="vs_draft_missing_category",
        )

    draft_key = f"vs_draft_text_{language}_{kind}_{missing_id or 'none'}"
    review_key = f"vs_draft_review_{language}_{kind}_{missing_id or 'none'}"
    if st.button(
        t("generate_draft", language),
        key="vs_generate_draft",
        type="primary",
    ):
        st.session_state[draft_key] = generate_draft(
            kind=kind,
            claim=claim,
            policy=policy,  # type: ignore[arg-type]
            provided_ids=provided_ids,
            missing_category_id=missing_id,
            language=language,
        )
        st.session_state[review_key] = False

    draft_text = st.text_area(
        t("draft_title", language),
        key=draft_key,
        height=360,
        placeholder=t("draft_empty", language),
    )
    reviewed = st.checkbox(t("draft_review_label", language), key=review_key)
    st.download_button(
        t("download_draft", language),
        data=draft_text,
        file_name=f"{claim.case_id}-{kind}-draft.txt",
        mime="text/plain",
        disabled=not reviewed or not draft_text.strip(),
        key=f"vs_download_{draft_key}",
    )
    st.caption(t("draft_demo_only", language))


def _valid_optional_date(value: str) -> bool:
    if not value.strip():
        return True
    try:
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def render_tracker(language: Language, claim: DemoClaim) -> dict[str, dict[str, object]]:
    st.subheader(t("tracker_title", language))
    st.caption(t("tracker_sub", language))
    st.write("")

    for step in claim.timeline:
        stage = step.stage_hi if language == "hi" else step.stage_en
        description = step.description_hi if language == "hi" else step.description_en
        with st.container(border=True):
            st.markdown(f"**{esc(stage)}**")
            st.caption(description)
            st.checkbox(t("mark_done", language), key=f"vs_step_done_{step.id}")
            due = st.text_input(
                t("due_date_label", language),
                key=f"vs_step_due_{step.id}",
                placeholder="YYYY-MM-DD",
                help=t("due_date_help", language),
            )
            if not _valid_optional_date(due):
                st.caption(t("due_date_invalid", language))
            st.text_area(
                t("notes_label", language),
                key=f"vs_step_notes_{step.id}",
                height=80,
                max_chars=1000,
            )

    tracker = current_tracker_state(claim)
    done = sum(1 for state in tracker.values() if state.get("done"))
    total = len(claim.timeline)
    st.progress(done / total if total else 0.0)
    st.caption(f"{done} / {total} {t('tracker_progress', language)}")
    return tracker


def render_escalation(language: Language) -> None:
    registry = load_source_registry()
    st.subheader(t("escalation_title", language))
    st.caption(t("escalation_sub", language))
    st.markdown(
        f"""
        <div class="vs-card">
          <p><strong>1.</strong> {esc(t('escalation_step_1', language))}</p>
          <p style="margin-top:10px;"><strong>2.</strong> {esc(t('escalation_step_2', language))}</p>
          <p style="margin-top:10px;"><strong>3.</strong> {esc(t('escalation_step_3', language))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(f"**{esc(t('escalation_links_title', language))}**")
    link_ids = [
        "irdai_gro_list",
        "bima_bharosa_faq",
        "bima_bharosa_portal",
        "council_insurance_ombudsmen",
    ]
    link_columns = st.columns(2)
    for index, source_id in enumerate(link_ids):
        source = registry.by_id(source_id)
        if source is None:
            continue
        with link_columns[index % 2]:
            st.link_button(source.title, source.url, width="stretch")
            st.caption(t("not_searched_note", language))
    st.write("")
    st.markdown(
        note(t("anti_fraud_warning", language), warning=True),
        unsafe_allow_html=True,
    )


def render_case_summary(
    language: Language,
    claim: DemoClaim,
    provided_ids: set[str],
    tracker: dict[str, dict[str, object]],
) -> None:
    policy = load_policy()
    summary = case_summary_text(claim, policy, provided_ids, tracker, language)
    st.subheader(t("case_summary_title", language))
    st.caption(t("case_summary_sub", language))
    st.download_button(
        t("download_case_summary", language),
        data=summary,
        file_name=f"{claim.case_id}-demo-summary.txt",
        mime="text/plain",
        key="vs_download_case_summary",
    )


def render_local_doc_check(language: Language) -> None:
    with st.expander(t("local_doc_title", language)):
        st.caption(t("local_doc_sub", language))
        acknowledged = st.checkbox(t("upload_ack_label", language), key="vs_doc_ack")
        uploaded = st.file_uploader(
            t("upload_doc", language),
            type=["pdf", "txt"],
            disabled=not acknowledged,
            key="vs_doc_upload",
            help=t("upload_doc_help", language),
        )
        st.session_state["vs_claim_doc_present"] = uploaded is not None
        st.caption(t("pdf_ocr_note", language))
        if uploaded is None:
            return
        raw = uploaded.getvalue()
        try:
            extension = validate_upload(
                uploaded.name, raw, allowed_extensions=frozenset({"pdf", "txt"})
            )
        except UploadError as exc:
            st.error(str(exc))
            return
        st.caption(t("uploaded_file_processed", language))
        st.caption(t("uploaded_doc_ai_disabled", language))
        if extension == "pdf":
            extraction = extract_pdf_text_in_memory(raw)
            st.info(extraction.message)
            for page in extraction.pages:
                with st.expander(f"{t('page_word', language)} {page.page_number}"):
                    st.text(page.text[:2000])
        else:
            try:
                text = extract_text_in_memory(raw)
            except UploadError as exc:
                st.error(str(exc))
                return
            st.code(text[:8000], language="text")
        st.caption(t("pdf_ocr_note", language))


def render_claims(language: Language) -> None:
    if st.button(t("back_home", language), key="vs_back_claims"):
        st.session_state["vs_page"] = "home"
        st.rerun()

    st.markdown(f"## {esc(t('claims_heading', language))}")
    st.caption(t("claims_sub", language))

    if not st.session_state.get("vs_claim_loaded", False):
        st.write("")
        st.markdown(
            f"""
            <div class="vs-card">
              <div class="vs-kicker">{esc(t('demo_case_label', language))} · DEMO-CLAIM-001</div>
              <h3>{esc(t('claims_card_title', language))}</h3>
              <p>{esc(t('claims_card_desc', language))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.button(
            t("load_demo_claim", language),
            key="vs_load_claim",
            type="primary",
            on_click=load_demo_claim_state,
            width="stretch",
        )
        st.caption(t("privacy_banner", language))
        return

    claim = load_claim()
    policy = load_policy()
    errors = validate_claim_against_policy(claim, policy)
    if errors:
        st.error(t("fixture_error", language) + ": " + "; ".join(errors))
        return

    provided_ids = current_provided_ids(claim)
    render_claim_overview(language, claim)
    st.write("")
    progress = checklist_progress(claim, provided_ids)
    total_metric, marked_metric, remaining_metric = st.columns(3)
    total_metric.metric(t("checklist_title", language), progress.total)
    marked_metric.metric(t("checklist_progress_marked", language), progress.marked)
    remaining_metric.metric(t("checklist_progress_remaining", language), progress.remaining)
    st.caption(t("checklist_progress_caption", language))

    st.divider()
    render_policy_facts(language)

    st.divider()
    provided_ids, _ = render_checklist(language, claim, provided_ids)

    st.divider()
    render_ai_panel(language, claim, provided_ids)

    st.divider()
    render_drafts(language, claim, policy, provided_ids)

    st.divider()
    tracker = render_tracker(language, claim)

    st.divider()
    render_escalation(language)

    st.divider()
    render_case_summary(language, claim, provided_ids, tracker)

    st.divider()
    render_local_doc_check(language)

    st.divider()
    render_sources_expander(language)


def render_lead_card(language: Language, lead, registry) -> None:
    with st.container(border=True):
        st.markdown(
            pill(category_label(lead.category_id, language), "vs-pill-info")
            + " "
            + pill(
                {
                    "low": t("strength_low", language),
                    "medium": t("strength_medium", language),
                    "strong_pattern": t("strength_strong", language),
                }[lead.pattern_strength],
                "vs-pill-neutral",
            ),
            unsafe_allow_html=True,
        )
        st.subheader(category_label(lead.category_id, language))
        st.caption(t("lead_note", language))

        st.markdown(f"**{esc(t('evidence_title', language))}**")
        for row in lead.evidence:
            st.markdown(
                f"""
                <div class="vs-evidence">
                  <strong>{esc(row.date.isoformat())}</strong> ·
                  {esc(row.description)} ·
                  {esc(format_inr(row.amount))} ·
                  {esc(row.direction)}
                  <span class="vs-mono"> · {esc(t('row_word', language))} {row.row_number}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(f"**{esc(t('rule_title', language))}**")
        st.write(lead.rule_hi if language == "hi" else lead.rule_en)
        st.markdown(f"**{esc(t('what_not_prove', language))}**")
        st.write(lead.does_not_prove_hi if language == "hi" else lead.does_not_prove_en)
        st.markdown(f"**{esc(t('next_step_label', language))}**")
        st.write(lead.next_step_hi if language == "hi" else lead.next_step_en)

        sources = registry.by_ids(lead.source_ids)
        if sources:
            st.markdown(f"**{esc(t('official_link_label', language))}**")
            for source in sources:
                st.link_button(source.title, source.url, width="stretch")
                st.caption(t("not_searched_note", language))
        else:
            st.caption(t("no_official_link", language))


def render_family_statement(language: Language) -> None:
    st.subheader(t("family_note_title", language))
    st.caption(t("family_note_help", language))
    st.text_area(
        t("family_note_title", language),
        key="vs_family_note",
        height=120,
        max_chars=1000,
        label_visibility="collapsed",
    )

    st.write("")
    st.subheader(t("family_steps_title", language))
    st.caption(t("family_steps_sub", language))
    step_keys = ["family_step_1", "family_step_2", "family_step_3"]
    done = 0
    for index, key in enumerate(step_keys, start=1):
        checked = st.checkbox(t(key, language), key=f"vs_family_step_{index}")
        done += 1 if checked else 0
    st.progress(done / len(step_keys))
    st.caption(f"{done} / {len(step_keys)} {t('family_progress', language)}")


def render_family(language: Language) -> None:
    if st.button(t("back_home", language), key="vs_back_family"):
        st.session_state["vs_page"] = "home"
        st.rerun()

    st.markdown(f"## {esc(t('family_heading', language))}")
    st.caption(t("family_sub", language))

    if not st.session_state.get("vs_family_loaded", False):
        st.write("")
        st.markdown(
            f"""
            <div class="vs-card">
              <div class="vs-kicker">{esc(t('synthetic_data_label', language))} · data/demo_transactions.csv</div>
              <h3>{esc(t('family_card_title', language))}</h3>
              <p>{esc(t('family_card_desc', language))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.button(
            t("load_synthetic", language),
            key="vs_load_family",
            type="primary",
            on_click=load_family_state,
            width="stretch",
        )
        st.caption(t("family_no_ai_note", language))
        return

    mode = st.radio(
        t("statement_mode_label", language),
        options=["demo", "upload"],
        format_func=lambda value: t("mode_demo" if value == "demo" else "mode_upload", language),
        horizontal=True,
        key="vs_family_mode",
    )

    rows = []
    uploaded = None
    parse_failed = False
    if mode == "demo":
        rows = parse_transactions_csv(load_demo_transactions_bytes())
        st.markdown(
            pill(t("synthetic_data_label", language), "vs-pill-demo"),
            unsafe_allow_html=True,
        )
        st.caption("data/demo_transactions.csv · " + t("family_no_ai_note", language))
    else:
        st.markdown(
            pill(t("local_upload_label", language), "vs-pill-demo"),
            unsafe_allow_html=True,
        )
        acknowledged = st.checkbox(t("upload_ack_label", language), key="vs_family_ack")
        uploaded = st.file_uploader(
            t("upload_csv_label", language),
            type=["csv"],
            disabled=not acknowledged,
            key="vs_family_upload",
            help=t("upload_csv_help", language),
        )
        st.session_state["vs_family_upload_present"] = uploaded is not None
        st.caption(t("upload_local_note", language))
        st.info(t("ai_disabled_upload", language))
        if uploaded is not None:
            raw = uploaded.getvalue()
            try:
                validate_upload(uploaded.name, raw, allowed_extensions=frozenset({"csv"}))
                rows = parse_transactions_csv(raw)
            except UploadError as exc:
                st.error(str(exc))
                rows = []
                parse_failed = True
            else:
                st.caption(t("uploaded_file_processed", language))
        else:
            st.caption(t("upload_csv_help", language))

    if not rows:
        st.write("")
        if mode == "upload" and uploaded is None:
            st.info(t("choose_csv", language))
        elif not parse_failed:
            st.info(t("no_leads", language))
        render_family_statement(language)
        render_sources_expander(language)
        return

    registry = load_source_registry()
    leads = match_transactions(rows)
    st.write("")
    row_metric, lead_metric, recurring_metric = st.columns(3)
    row_metric.metric(t("statement_rows_metric", language), len(rows))
    lead_metric.metric(t("leads_found", language), len(leads))
    recurring_metric.metric(
        t("recurring_patterns_metric", language),
        sum(1 for lead in leads if lead.is_recurring),
    )

    st.subheader(t("family_results_title", language))
    st.caption(t("family_results_sub", language))
    if not leads:
        st.info(t("no_leads", language))
    else:
        for lead in leads:
            render_lead_card(language, lead, registry)

    with st.expander(t("statement_rows_title", language)):
        st.dataframe(
            [
                {
                    t("table_row", language): row.row_number,
                    t("table_date", language): row.date.isoformat(),
                    t("table_description", language): row.description,
                    t("table_amount", language): format_inr(row.amount),
                    t("table_direction", language): row.direction,
                }
                for row in rows
            ],
            hide_index=True,
            width="stretch",
        )

    st.divider()
    render_family_statement(language)
    st.divider()
    render_sources_expander(language)


def render_footer(language: Language) -> None:
    st.markdown(
        f"""
        <div class="vs-footer">
          <strong>{esc(t('independent', language))}</strong><br/>
          {esc(t('footer_note', language))}<br/>
          {esc(t('footer_rule', language))} · {esc(t('footer_license', language))}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render_css()
    init_session()
    user = current_auth_user()
    if user is None:
        render_login()
        return
    st.session_state["vs_insurance_active_user_id"] = str(user["demo_user_id"])
    language = render_header()
    render_privacy_banner(language)
    render_top_nav(language)
    page = st.session_state.get("vs_page", "home")
    if page == "claims":
        render_claims(language)
    elif page == "family":
        render_family(language)
    elif page == "insurance":
        render_active_insurances(language)
    else:
        render_home(language)
    render_footer(language)


if __name__ == "__main__":
    main()
