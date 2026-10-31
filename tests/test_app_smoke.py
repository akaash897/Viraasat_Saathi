from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def new_login_screen() -> AppTest:
    """Return the app at the login screen (no user signed in)."""
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def login(at: AppTest, login_id: str = "aarav") -> None:
    """Sign in using preset credentials."""
    passwords = {"aarav": "aarav123", "meera": "meera123"}
    password = passwords.get(login_id, "aarav123")
    at.text_input(key="vs_login_id").set_value(login_id)
    at.text_input(key="vs_login_password").set_value(password)
    at.button(key="vs_login_submit").click().run()


def new_app(user: str = "aarav") -> AppTest:
    """Return the app after signing in as the given preset user."""
    at = new_login_screen()
    login(at, user)
    return at


def visible_text(at: AppTest) -> str:
    """Collect user-visible text, excluding CSS style blocks."""
    parts: list[str] = []
    for item in at.markdown:
        val = str(item.value)
        if "<style>" not in val:
            parts.append(val)
    for item in at.caption:
        parts.append(str(item.value))
    for item in at.info:
        parts.append(str(item.value))
    for item in at.warning:
        parts.append(str(item.value))
    for item in at.error:
        parts.append(str(item.value))
    for item in at.success:
        parts.append(str(item.value))
    return "\n".join(parts)


def has_widget(at: AppTest, collection: str, key: str) -> bool:
    """Check if a widget exists without raising KeyError."""
    try:
        # ChatInput might be in a different collection
        if collection == "chat_input":
            # ChatInput is a special widget type
            for item in getattr(at, "chat_input", []):
                if getattr(item, "key", None) == key:
                    return True
            return False
        getattr(at, collection)(key=key)
        return True
    except KeyError:
        return False
    except AttributeError:
        return False


def has_button(at: AppTest, key: str) -> bool:
    return has_widget(at, "button", key)


def has_radio(at: AppTest, key: str) -> bool:
    return has_widget(at, "radio", key)


def has_text_input(at: AppTest, key: str) -> bool:
    return has_widget(at, "text_input", key)


def has_toggle(at: AppTest, key: str) -> bool:
    return has_widget(at, "toggle", key)


def test_login_screen_shows_no_demo_wording() -> None:
    at = new_login_screen()
    assert not at.exception
    text = visible_text(at).lower()
    assert "prototype" in text
    assert "sign in" in text
    assert "paytm-style experience" in text
    assert "demo" not in text
    assert "simulated" not in text
    assert has_button(at, "vs_login_submit")
    assert has_text_input(at, "vs_login_id")
    assert has_text_input(at, "vs_login_password")
    assert not has_radio(at, "vs_language_choice")
    assert not has_button(at, "vs_reset")


def test_login_rejects_wrong_credentials() -> None:
    at = new_login_screen()
    at.text_input(key="vs_login_id").set_value("aarav")
    at.text_input(key="vs_login_password").set_value("wrong")
    at.button(key="vs_login_submit").click().run()
    assert not at.exception
    assert at.session_state["vs_auth_user_id"] is None
    assert any("does not match" in str(e.value) for e in at.error)


def test_login_with_correct_credentials_shows_home_and_profile() -> None:
    at = new_login_screen()
    login(at, "aarav")
    assert not at.exception
    assert at.session_state["vs_auth_user_id"] == "paytm.demo.aarav"
    assert at.session_state["vs_page"] == "home"
    text = visible_text(at)
    assert "Aarav Sharma" in text
    assert "Active Insurances" in text
    assert "Nominee 360" in text
    assert "AI Assistant" in text
    # Logout button exists in header
    assert has_button(at, "vs_logout")
    assert "Independent hackathon prototype" in text
    assert "Do not upload real" in text
    assert "Synthetic data" in text
    # No language toggle, no reset
    assert not has_radio(at, "vs_language_choice")
    assert not has_button(at, "vs_reset")


def test_logout_returns_to_login_and_preserves_session_state() -> None:
    at = new_app("aarav")
    at.button(key="vs_open_nominee360").click().run()
    assert not at.exception
    at.button(key="vs_logout").click().run()
    assert not at.exception
    assert at.session_state["vs_auth_user_id"] is None
    assert at.session_state["vs_page"] == "home"
    # Back at login screen
    assert has_button(at, "vs_login_submit")
    # Re-login preserves auth
    login(at, "aarav")
    assert at.session_state["vs_auth_user_id"] == "paytm.demo.aarav"


def test_home_renders_three_journeys_and_privacy() -> None:
    at = new_app()
    assert not at.exception
    text = visible_text(at)
    assert "Active Insurances" in text
    assert "Nominee 360" in text
    assert "AI Assistant" in text
    assert "Do not upload real medical" in text
    assert "Independent hackathon prototype" in text
    assert {button.key for button in at.button} >= {
        "vs_logout",
        "vs_open_insurance",
        "vs_open_nominee360",
        "vs_open_chatbot",
    }


def test_claims_ai_panel_shows_sarvam_status() -> None:
    """Claims AI panel removed - this test is now a placeholder."""
    # The Claims Companion journey has been removed.
    # This test verifies the old button no longer exists.
    at = new_app()
    assert not has_button(at, "vs_open_claims")
    assert not has_button(at, "vs_load_claim")


def test_english_only_no_language_toggle() -> None:
    at = new_app()
    # No language radio anywhere in the app after login
    assert not has_radio(at, "vs_language_choice")
    # Privacy banner still renders in English
    text = visible_text(at)
    assert "Independent hackathon prototype" in text
    assert "Do not upload real" in text
    # No Hindi strings
    assert "दावा साथी" not in text
    assert "परिवार वित्त खोजक" not in text


def test_chatbot_page_loads() -> None:
    """Test AI Assistant chatbot page loads."""
    at = new_app()
    at.button(key="vs_nav_chatbot").click().run()
    assert not at.exception
    # Check for chat input (may be chat_input or text_input depending on Streamlit version)
    assert has_widget(at, "chat_input", "vs_chatbot_input") or has_widget(at, "text_input", "vs_chatbot_input")