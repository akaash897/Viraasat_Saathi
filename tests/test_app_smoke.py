from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def new_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def all_markdown(at: AppTest) -> str:
    return "\n".join(str(item.value) for item in at.markdown)


def metric_values(at: AppTest, label: str) -> list[str]:
    return [str(item.value) for item in at.metric if item.label == label]


def test_home_renders_both_journeys_and_privacy() -> None:
    at = new_app()
    assert not at.exception
    markdown = all_markdown(at)
    assert "Claims Companion" in markdown
    assert "Family Finance Finder" in markdown
    assert "Hackathon prototype" in markdown
    assert "Do not upload real medical" in markdown
    assert "Independent hackathon prototype" in markdown
    assert {button.key for button in at.button} >= {
        "vs_reset",
        "vs_open_claims",
        "vs_open_family",
    }


def test_claims_flow_checklist_draft_tracker_and_reset() -> None:
    at = new_app()
    at.button(key="vs_open_claims").click().run()
    assert not at.exception
    at.button(key="vs_load_claim").click().run()
    assert not at.exception
    assert "DEMO-CLAIM-001" in all_markdown(at)
    assert metric_values(at, "Still unmarked")[0] == "7"

    at.checkbox(key="vs_provided_claim_form").check().run()
    assert not at.exception
    assert metric_values(at, "Still unmarked")[0] == "6"

    at.checkbox(key="vs_provided_policy_schedule").check().run()
    assert not at.exception
    assert metric_values(at, "Still unmarked")[0] == "5"

    at.button(key="vs_generate_draft").click().run()
    assert not at.exception
    draft_download = at.download_button(
        key="vs_download_vs_draft_text_en_missing_document_followup_claim_form"
    )
    assert draft_download.disabled is True
    at.checkbox(
        key="vs_draft_review_en_missing_document_followup_claim_form"
    ).check().run()
    assert not at.exception
    assert (
        at.download_button(
            key="vs_download_vs_draft_text_en_missing_document_followup_claim_form"
        ).disabled
        is False
    )

    at.checkbox(key="vs_step_done_step_confirm_list").check().run()
    assert not at.exception
    assert at.progress

    at.button(key="vs_reset").click().run()
    assert not at.exception
    assert at.session_state["vs_claim_loaded"] is False
    assert {button.key for button in at.button} >= {"vs_open_claims", "vs_open_family"}


def test_family_flow_leads_evidence_links_and_upload_gate() -> None:
    at = new_app()
    at.button(key="vs_open_family").click().run()
    assert not at.exception
    at.button(key="vs_load_family").click().run()
    assert not at.exception
    assert metric_values(at, "possible leads found")[0] == "4"
    assert metric_values(at, "Recurring patterns")[0] == "4"
    markdown = all_markdown(at)
    for category in (
        "Possible insurance payment",
        "Possible investment or SIP",
        "Possible lender or EMI",
        "Possible recurring subscription",
    ):
        assert category in markdown
    assert "does not prove" in markdown.lower()
    captions = "\n".join(str(item.value) for item in at.caption)
    assert "We have not searched this portal" in captions
    urls = {link.url for link in at.link_button}
    assert "https://bimabharosa.irdai.gov.in/Home/FAQ" in urls
    assert "https://www.unclaimedassetsportal.in/" in urls
    assert "https://udgam.rbi.org.in/unclaimed-deposits/#/login" in urls

    at.radio(key="vs_family_mode").set_value("upload").run()
    assert not at.exception
    assert at.file_uploader(key="vs_family_upload").disabled is True
    assert any(
        "AI is disabled for user-supplied records" in str(info.value)
        for info in at.info
    )


def test_language_toggle_renders_hindi_safety_copy() -> None:
    at = new_app()
    at.radio(key="vs_language_choice").set_value("hi").run()
    assert not at.exception
    markdown = all_markdown(at)
    assert "दावा साथी" in markdown
    assert "परिवार वित्त खोजक" in markdown
    assert "काल्पनिक डेमो केस" in markdown
    assert "वास्तविक चिकित्सा" in markdown


def test_claims_ai_panel_is_disabled_without_key() -> None:
    at = new_app()
    at.button(key="vs_open_claims").click().run()
    at.button(key="vs_load_claim").click().run()
    assert not at.exception
    captions = "\n".join(str(item.value) for item in at.caption)
    assert "Sarvam status" in captions
    assert "Off" in captions
    assert at.toggle(key="vs_sarvam_opt_in").disabled is True


def test_reset_clears_family_note_and_steps() -> None:
    at = new_app()
    at.button(key="vs_open_family").click().run()
    at.button(key="vs_load_family").click().run()
    at.text_area(key="vs_family_note").set_value("Synthetic note only").run()
    at.checkbox(key="vs_family_step_1").check().run()
    assert not at.exception
    at.button(key="vs_reset").click().run()
    assert not at.exception
    assert at.session_state["vs_family_loaded"] is False
    assert "vs_family_note" not in at.session_state
    assert "vs_family_step_1" not in at.session_state
