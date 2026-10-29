from __future__ import annotations

import inspect
import logging
from typing import Literal, get_args, get_type_hints

import pytest

from src.sarvam_service import (
    FIXED_SOURCE_EXCERPTS,
    SarvamConfig,
    SarvamService,
)


def configured_service(**overrides) -> SarvamService:
    values = {
        "api_key": "test-key-not-real",
        "model": "gemma4",
        "base_url": "https://api.sarvam.ai/v2",
        "enabled_flag": True,
    }
    values.update(overrides)
    return SarvamService(SarvamConfig(**values))


def test_sarvam_payload_no_free_text() -> None:
    signature = inspect.signature(SarvamService.explain_demo_checklist)
    assert set(signature.parameters) == {
        "self",
        "language",
        "claim_type",
        "missing_category",
        "source_excerpt_id",
    }
    hints = get_type_hints(SarvamService.explain_demo_checklist)
    assert set(get_args(hints["language"])) == {"en", "hi"}
    assert set(get_args(hints["claim_type"])) == {"health_reimbursement"}
    assert "claim_form" in get_args(hints["missing_category"])
    assert set(get_args(hints["source_excerpt_id"])) == {
        "demo_policy_clause_01",
        "demo_checklist_01",
    }
    for forbidden in ("text", "content", "prompt", "document", "rows", "message"):
        assert forbidden not in signature.parameters


def test_disabled_mode_uses_deterministic_fallback() -> None:
    service = SarvamService(
        SarvamConfig(enabled_flag=False, api_key="test-key-not-real")
    )
    english = service.explain_demo_checklist(
        "en", "health_reimbursement", "claim_form", "demo_policy_clause_01"
    )
    assert english.status == "disabled"
    assert english.ai_used is False
    assert "demo checklist" in english.text.lower()

    hindi = service.explain_demo_checklist(
        "hi", "health_reimbursement", "claim_form", "demo_policy_clause_01"
    )
    assert hindi.status == "disabled"
    assert hindi.ai_used is False
    assert "डेमो" in hindi.text


def test_missing_key_is_disabled() -> None:
    config = SarvamConfig.from_env(
        {"SARVAM_ENABLED": "true", "SARVAM_API_KEY": "", "SARVAM_MODEL": "gemma4"}
    )
    assert config.is_configured is False
    assert config.status_key == "sarvam_status_no_key"


def test_deprecated_model_is_not_configured() -> None:
    config = SarvamConfig.from_env(
        {
            "SARVAM_ENABLED": "true",
            "SARVAM_API_KEY": "test-key-not-real",
            "SARVAM_MODEL": "sarvam-30b",
        }
    )
    assert config.is_configured is False
    assert config.status_key == "sarvam_status_deprecated_model"


def test_sarvam_success(monkeypatch) -> None:
    service = configured_service()
    monkeypatch.setattr(
        service,
        "_call_api",
        lambda messages: "The demo checklist lists a completed claim form. Confirm with the insurer.",
    )
    result = service.explain_demo_checklist(
        "en", "health_reimbursement", "claim_form", "demo_policy_clause_01"
    )
    assert result.status == "success"
    assert result.ai_used is True
    assert "completed claim form" in result.text
    assert result.note_key == "sarvam_ai_note"


def test_sarvam_error_fallback(monkeypatch, caplog) -> None:
    service = configured_service()

    def explode(messages):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(service, "_call_api", explode)
    with caplog.at_level(logging.INFO):
        result = service.explain_demo_checklist(
            "en", "health_reimbursement", "itemised_bill", "demo_policy_clause_01"
        )
    assert result.status == "fallback"
    assert result.ai_used is False
    assert result.text
    assert "status=fallback" in caplog.text
    assert FIXED_SOURCE_EXCERPTS["demo_policy_clause_01"] not in caplog.text


def test_sarvam_malformed_response_fallback(monkeypatch) -> None:
    service = configured_service()
    for bad in ("", "   ", "Your claim is approved and guaranteed.", "x" * 2000):
        monkeypatch.setattr(service, "_call_api", lambda messages, bad=bad: bad)
        result = service.explain_demo_checklist(
            "en", "health_reimbursement", "payment_receipt", "demo_checklist_01"
        )
        assert result.status == "fallback"
        assert result.ai_used is False


def test_sarvam_prompt_contains_only_fixed_synthetic_content(monkeypatch) -> None:
    service = configured_service()
    captured: list[list[dict[str, str]]] = []

    def capture(messages):
        captured.append(messages)
        return "A short non-adjudicative paraphrase."

    monkeypatch.setattr(service, "_call_api", capture)
    service.explain_demo_checklist(
        "hi", "health_reimbursement", "supporting_reports", "demo_policy_clause_01"
    )
    assert len(captured) == 1
    joined = "\n".join(message["content"] for message in captured[0])
    assert FIXED_SOURCE_EXCERPTS["demo_policy_clause_01"] in joined
    assert "supporting_reports" in joined
    assert "health_reimbursement" in joined
    assert "Hindi" in joined
    assert "approved" in joined.lower()  # only the instruction forbids approval
    assert "Do not say a claim is approved" in joined


def test_unknown_enum_values_are_rejected() -> None:
    service = configured_service()
    with pytest.raises(ValueError):
        service.explain_demo_checklist(
            "en", "health_reimbursement", "unknown_category", "demo_policy_clause_01"  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        service.explain_demo_checklist(
            "en", "health_reimbursement", "claim_form", "user_uploaded_text"  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        service.explain_demo_checklist(
            "fr", "health_reimbursement", "claim_form", "demo_policy_clause_01"  # type: ignore[arg-type]
        )


def test_config_defaults_and_env(monkeypatch) -> None:
    config = SarvamConfig.from_env({})
    assert config.model == "gemma4"
    assert config.base_url == "https://api.sarvam.ai/v2"
    assert config.enabled_flag is False
    assert config.is_configured is False
    assert config.status_key == "sarvam_status_disabled"

    config = SarvamConfig.from_env(
        {
            "SARVAM_ENABLED": "true",
            "SARVAM_API_KEY": "test-key-not-real",
            "SARVAM_MODEL": "glm5.3",
            "SARVAM_BASE_URL": "https://api.sarvam.ai/v2/",
        }
    )
    assert config.is_configured is True
    assert config.base_url == "https://api.sarvam.ai/v2"
