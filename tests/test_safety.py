from __future__ import annotations

import builtins
import io
from pathlib import Path

import pytest

from src.document_parser import (
    MAX_UPLOAD_BYTES,
    UploadError,
    extract_pdf_text_in_memory,
    validate_upload,
)
from src.fixtures import load_source_registry
from src.safety import (
    SAFETY_KEYS,
    contains_adjudicative_claim,
    format_inr,
    is_official_https,
    reset_session_state,
)
from src.translations import TRANSLATIONS, t


def test_reset_clears_session() -> None:
    state = {
        "vs_page": "claims",
        "vs_lang": "hi",
        "vs_provided_claim_form": True,
        "unrelated": "keep-me",
    }
    removed = reset_session_state(state)
    assert removed == 3
    assert state == {"unrelated": "keep-me"}


def test_translation_keys_match() -> None:
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["hi"])
    for key in SAFETY_KEYS:
        assert t(key, "en")
        assert t(key, "hi")


def test_safety_copy_contains_required_warnings() -> None:
    english = t("privacy_banner", "en").lower()
    assert "do not upload real" in english
    assert "synthetic records" in english

    fraud = t("anti_fraud_warning", "en").lower()
    for term in ("fee", "qr code", "otp", "upi pin", "password"):
        assert term in fraud

    hindi_fraud = t("anti_fraud_warning", "hi")
    for term in ("शुल्क", "QR", "OTP", "UPI पिन", "पासवर्ड"):
        assert term in hindi_fraud

    disclaimer = t("claims_disclaimer", "en").lower()
    assert "does not decide" in disclaimer
    assert "not an insurer" in disclaimer

    draft_note = t("draft_no_submission", "en").lower()
    assert "nothing is sent" in draft_note


def test_source_registry_uses_https_and_required_sources() -> None:
    registry = load_source_registry()
    required = {
        "irdai_health_dept",
        "bima_bharosa_faq",
        "bima_bharosa_portal",
        "irdai_gro_list",
        "council_insurance_ombudsmen",
        "common_landing_portal",
        "rbi_udgam",
        "sarvam_openweight_docs",
        "sarvam_model_status",
        "dpdp_rules_backgrounder",
    }
    ids = {source.id for source in registry.sources}
    assert required <= ids
    expected_urls = {
        "irdai_health_dept": "https://irdai.gov.in/health-dept",
        "bima_bharosa_faq": "https://bimabharosa.irdai.gov.in/Home/FAQ",
        "bima_bharosa_portal": "https://bimabharosa.irdai.gov.in/",
        "irdai_gro_list": "https://irdai.gov.in/list-of-gros",
        "council_insurance_ombudsmen": "https://www.cioins.co.in/Ombudsman",
        "common_landing_portal": "https://www.unclaimedassetsportal.in/",
        "rbi_udgam": "https://udgam.rbi.org.in/unclaimed-deposits/#/login",
        "sarvam_openweight_docs": (
            "https://docs.sarvam.ai/api/getting-started/models/openweight"
        ),
        "sarvam_model_status": "https://docs.sarvam.ai/api/getting-started/models",
        "dpdp_rules_backgrounder": (
            "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190655&lang=2&reg=48"
        ),
    }
    for source_id, url in expected_urls.items():
        assert registry.by_id(source_id).url == url
    for source in registry.sources:
        assert source.url.startswith("https://")
        assert is_official_https(source.url)
        assert source.checked_on
        assert "does not" in source.notes.lower() or "not" in source.notes.lower()
    assert "does not query" in registry.registry_note_en.lower()


def test_adjudicative_terms_are_detected() -> None:
    assert contains_adjudicative_claim("Your claim is approved and guaranteed.")
    assert contains_adjudicative_claim("You are eligible for a payout.")
    assert not contains_adjudicative_claim(
        "The demo checklist lists a completed claim form; confirm with the insurer."
    )


def test_format_inr() -> None:
    assert format_inr("1850") == "₹1,850.00"


def test_upload_size_limit() -> None:
    with pytest.raises(UploadError):
        validate_upload("statement.csv", b"x" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(UploadError):
        validate_upload("statement.exe", b"x")
    with pytest.raises(UploadError):
        validate_upload("statement.csv", b"")
    assert validate_upload("statement.csv", b"a,b\n1,2\n") == "csv"


def _blank_pdf_bytes() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_parser_no_disk_write(monkeypatch) -> None:
    writes: list[str] = []
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            writes.append(str(file))
            raise AssertionError("the PDF parser attempted to write to disk")
        return real_open(file, mode, *args, **kwargs)

    def guarded_write(*args, **kwargs):
        writes.append(str(args[0]) if args else "unknown")
        raise AssertionError("the PDF parser attempted to write to disk")

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "write_bytes", guarded_write)
    monkeypatch.setattr(Path, "write_text", guarded_write)

    result = extract_pdf_text_in_memory(_blank_pdf_bytes())
    assert result.readable is False
    assert result.ocr_supported is False
    assert "OCR is not supported" in result.message
    assert writes == []
