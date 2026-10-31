from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from streamlit.testing.v1 import AppTest

from src.insurance_inventory import (
    NOT_FOUND,
    display_value,
    limited_shared_summary,
    link_is_visible_to_nominee,
    nominee_status_label,
    paytm_policies_for_user,
    reset_insurance_session,
    seeded_paytm_records,
)
from src.mock_paytm_data import seeded_nominee_links_as_dicts, users_as_dicts
from src.nominee_demo import (
    NomineeError,
    create_nominee_link,
    respond_to_nominee_link,
    revoke_nominee_link,
)
from src.policy_normalizer import (
    build_external_policy,
    classify_document,
    review_external_policy,
)
from src.sarvam_document_ai import (
    DocumentAiConfig,
    DocumentAiError,
    DocumentAiJobFailed,
    DocumentAiNotConfigured,
    DocumentAiTimeout,
    SarvamDocumentAI,
)
from src.upload_validation import (
    MAX_UPLOAD_BYTES,
    UploadValidationError,
    validate_insurance_upload,
)

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "app.py"


def pdf_bytes(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"demo-image"


def jpg_bytes() -> bytes:
    return b"\xff\xd8\xff" + b"demo-image"


class FakeDocAi:
    def __init__(self, statuses, result, *, raise_on_extract=None):
        self.statuses = list(statuses)
        self.result = result
        self.raise_on_extract = raise_on_extract
        self.index = 0
        self.extract_kwargs = None
        self.status_calls = 0
        self.result_calls = 0

    def extract(self, **kwargs):
        self.extract_kwargs = kwargs
        if self.raise_on_extract is not None:
            raise self.raise_on_extract
        return {"job_id": "job-demo-1", "status": "pending", "run_id": "run-1"}

    def get_status(self, job_id):
        self.status_calls += 1
        status = self.statuses[min(self.index, len(self.statuses) - 1)]
        self.index += 1
        return SimpleNamespace(status=status, job_id=job_id)

    def get_results(self, job_id):
        self.result_calls += 1
        return {
            "type": "extract",
            "job_id": job_id,
            "status": "completed",
            "result": self.result,
            "annotations": {},
            "version": 1,
        }


class FakeClient:
    def __init__(self, doc_ai):
        self.doc_ai = doc_ai


def configured_document_ai(doc_ai, **overrides) -> SarvamDocumentAI:
    values = {
        "api_key": "test-key-not-real",
        "enabled_flag": True,
        "language": "en-IN",
        "job_timeout_seconds": 60.0,
        "poll_interval_seconds": 0.1,
    }
    values.update(overrides)
    config = DocumentAiConfig(**values)
    return SarvamDocumentAI(
        config,
        client_factory=lambda _config: FakeClient(doc_ai),
        sleep=lambda _seconds: None,
    )


def paytm_policy(policy_id: str = "demo-pol-aarav-health-01"):
    return next(
        record
        for record in seeded_paytm_records()
        if record["policy_id"] == policy_id
    )


def external_extraction(**overrides):
    result = {
        "document_type": "Insurance policy",
        "insurer_name": "Example Demo Insurance Co.",
        "product_name": "Example Demo Health Plan",
        "policyholder_name": "Demo Holder",
        "insured_persons": "Demo Holder",
        "policy_number": "POL-DEMO-123456",
        "uin": "DEMO-UIN-001",
        "policy_start_date": "01/04/2026",
        "policy_end_date": "31/03/2027",
        "sum_insured": "INR 5,00,000",
        "premium_amount": "INR 12,000",
        "premium_frequency": "Annual",
        "nominee_name": "Demo Nominee",
        "nominee_relationship": "Spouse",
    }
    result.update(overrides)
    return result


def test_mock_paytm_user_switch_filters_policies() -> None:
    records = seeded_paytm_records()
    aarav = paytm_policies_for_user(records, "paytm.demo.aarav")
    meera = paytm_policies_for_user(records, "paytm.demo.meera")

    assert len(aarav) >= 2
    assert len(meera) >= 1
    assert {record["product_type"] for record in aarav} >= {"health", "motor"}
    assert not {record["policy_id"] for record in aarav} & {
        record["policy_id"] for record in meera
    }
    assert all(record["source_type"] == "PAYTM_DEMO" for record in records)
    assert all(
        record["verification_status"] == "SIMULATED_NOT_VERIFIED"
        for record in records
    )
    assert all("•" in record["policy_number_masked"] for record in records)


def test_no_paytm_network_calls() -> None:
    modules = [
        ROOT / "src" / "mock_paytm_data.py",
        ROOT / "src" / "nominee_demo.py",
        ROOT / "src" / "insurance_inventory.py",
        ROOT / "src" / "insurance_ui.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in modules)
    assert "http://" not in source
    assert "https://" not in source
    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "aiohttp",
        "paytmpayments",
        "paytm.com",
    ):
        assert forbidden not in source

    fixtures = "\n".join(
        (ROOT / "data" / name).read_text(encoding="utf-8")
        for name in (
            "mock_paytm_users.json",
            "mock_paytm_policies.json",
            "mock_nominee_links.json",
        )
    )
    assert not re.search(r"\b[6-9]\d{9}\b", fixtures)
    assert "@" not in fixtures
    assert "paytm.demo." in fixtures


def test_upload_file_type_and_size() -> None:
    pdf = validate_insurance_upload("policy.pdf", pdf_bytes(1))
    assert pdf.mime_type == "application/pdf"
    assert pdf.page_count == 1

    assert validate_insurance_upload("scan.png", png_bytes()).mime_type == "image/png"
    assert validate_insurance_upload("scan.jpg", jpg_bytes()).mime_type == "image/jpeg"
    assert validate_insurance_upload("scan.jpeg", jpg_bytes()).extension == "jpeg"

    with pytest.raises(UploadValidationError, match="Unsupported file type"):
        validate_insurance_upload("policy.zip", b"PK\x03\x04demo")
    with pytest.raises(UploadValidationError, match="Unsupported file type"):
        validate_insurance_upload("policy.tiff", b"II*\x00demo")
    with pytest.raises(UploadValidationError, match="empty"):
        validate_insurance_upload("policy.pdf", b"")
    with pytest.raises(UploadValidationError, match="10 MB"):
        validate_insurance_upload(
            "policy.pdf", b"%PDF-" + b"x" * MAX_UPLOAD_BYTES
        )
    with pytest.raises(UploadValidationError, match="does not match"):
        validate_insurance_upload("policy.pdf", png_bytes())
    with pytest.raises(UploadValidationError, match="20 pages"):
        validate_insurance_upload("large.pdf", pdf_bytes(21))


def test_sarvam_missing_key_is_disabled_and_makes_no_call() -> None:
    config = DocumentAiConfig.from_env(
        {"SARVAM_ENABLED": "true", "SARVAM_API_KEY": "replace_with_your_key"}
    )
    assert config.is_configured is False
    assert "Add SARVAM_API_KEY to .env" in config.disabled_message

    called: list[object] = []

    def factory(_config):
        called.append(_config)
        raise AssertionError("factory must not be called")

    service = SarvamDocumentAI(config, client_factory=factory)
    with pytest.raises(DocumentAiNotConfigured) as excinfo:
        service.extract_policy(
            pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
        )
    assert "Add SARVAM_API_KEY to .env" in str(excinfo.value)
    assert called == []


def test_sarvam_extract_job_lifecycle(caplog) -> None:
    result = external_extraction()
    doc_ai = FakeDocAi(["pending", "running", "completed"], result)
    service = configured_document_ai(doc_ai)
    with caplog.at_level(logging.INFO):
        outcome = service.extract_policy(
            pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
        )

    assert outcome.job_id == "job-demo-1"
    assert outcome.status == "completed"
    assert outcome.result == result
    assert outcome.partial is False
    assert doc_ai.status_calls == 3
    assert doc_ai.result_calls == 1

    kwargs = doc_ai.extract_kwargs
    assert kwargs is not None
    assert kwargs["file"][0][0] == "policy.pdf"
    assert kwargs["file"][0][2] == "application/pdf"
    assert kwargs["output_format"] == "json"
    assert json.loads(kwargs["schema"])["type"] == "object"
    assert kwargs["request_options"]["additional_body_parameters"]["language"] == "en-IN"
    assert "POL-DEMO-123456" not in caplog.text
    assert "Example Demo Insurance Co." not in caplog.text
    assert "test-key-not-real" not in caplog.text


def test_sarvam_accepts_object_results_and_partial_completion() -> None:
    doc_ai = FakeDocAi(["pending", "partially_completed"], external_extraction())
    doc_ai.get_results = lambda job_id: SimpleNamespace(
        status="partially_completed",
        result={"document_type": "Insurance policy"},
    )
    outcome = configured_document_ai(doc_ai).extract_policy(
        pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
    )
    assert outcome.status == "partially_completed"
    assert outcome.partial is True
    assert outcome.result == {"document_type": "Insurance policy"}


def test_sarvam_timeout_and_failure_paths() -> None:
    timeout_ai = FakeDocAi(["pending"], external_extraction())
    clock = [0.0]
    service = SarvamDocumentAI(
        DocumentAiConfig(
            api_key="test-key-not-real",
            enabled_flag=True,
            job_timeout_seconds=1.0,
            poll_interval_seconds=0.5,
        ),
        client_factory=lambda _config: FakeClient(timeout_ai),
        clock=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    with pytest.raises(DocumentAiTimeout, match="did not finish"):
        service.extract_policy(
            pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
        )

    for status in ("failed", "rejected"):
        doc_ai = FakeDocAi([status], external_extraction())
        with pytest.raises(DocumentAiJobFailed, match="No policy was added"):
            configured_document_ai(doc_ai).extract_policy(
                pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
            )

    error_ai = FakeDocAi(
        ["pending"], external_extraction(), raise_on_extract=RuntimeError("boom")
    )
    with pytest.raises(DocumentAiError, match="No policy was added"):
        configured_document_ai(error_ai).extract_policy(
            pdf_bytes(1), filename="policy.pdf", mime_type="application/pdf"
        )


def test_extraction_missing_fields_not_invented() -> None:
    result = build_external_policy(
        {"document_type": "Insurance policy", "policy_number": "Not found in document"},
        document_name="scan.pdf",
        owner_demo_user_id="paytm.demo.aarav",
    )
    assert result.added is True
    assert result.record is not None
    record = result.record
    for field in (
        "insurer_name",
        "product_name",
        "policy_number_masked",
        "policy_number_full",
        "uin",
        "policy_start_date",
        "policy_end_date",
        "sum_insured",
        "premium_amount",
        "premium_frequency",
        "policyholder_name",
        "ocr_nominee_name",
        "ocr_nominee_relationship",
    ):
        assert record[field] is None
    assert record["insured_persons"] == []
    assert display_value(record["insurer_name"]) == NOT_FOUND
    assert display_value(record["policy_start_date"]) == NOT_FOUND
    assert any("not found" in reason.lower() for reason in record["review_reasons"])


def test_ocr_record_created_needs_review_and_user_review() -> None:
    result = build_external_policy(
        external_extraction(),
        document_name="my-policy.pdf",
        owner_demo_user_id="paytm.demo.aarav",
    )
    assert result.added is True
    assert result.record is not None
    record = result.record
    assert record["source_type"] == "EXTERNAL_DOCUMENT"
    assert record["verification_status"] == "OCR_EXTRACTED_NEEDS_REVIEW"
    assert record["owner_demo_user_id"] == "paytm.demo.aarav"
    assert record["policy_number_full"] == "POL-DEMO-123456"
    assert record["policy_number_masked"] != record["policy_number_full"]
    assert record["policy_start_date"] == "2026-04-01"
    assert "insurer status not checked" in record["display_status"].lower()
    assert "active" not in record["display_status"].lower()

    with pytest.raises(ValueError, match="authorised"):
        review_external_policy(
            record, {"insurer_name": "Corrected"}, authorised=False
        )

    reviewed = review_external_policy(
        record,
        {
            "insurer_name": "Corrected Demo Insurer",
            "product_type": "health",
            "policy_number_full": "CORRECTED-9999",
            "policy_start_date": "2026-04-02",
        },
        authorised=True,
    )
    assert reviewed["verification_status"] == "USER_REVIEWED_UNVERIFIED"
    assert reviewed["insurer_name"] == "Corrected Demo Insurer"
    assert reviewed["policy_number_masked"] != "CORRECTED-9999"
    assert reviewed["policy_start_date"] == "2026-04-02"
    assert reviewed["raw_extracted"]["insurer_name"] == "Example Demo Insurance Co."
    assert "insurer status not checked" in reviewed["display_status"].lower()


def test_non_policy_document_not_added() -> None:
    assert classify_document({"document_type": "Bank account statement"}) == (
        "not_insurance"
    )
    for extracted in (
        {
            "document_type": "Bank account statement",
            "insurer_name": "Example Demo Insurance Co.",
            "product_name": "Example Demo Health Plan",
        },
        {"document_type": "Invoice", "policy_number": "INV-001"},
        {
            "document_type": "Insurance premium receipt",
            "insurer_name": "Example Demo Insurance Co.",
            "policy_number": "POL-DEMO-123456",
        },
        {"document_type": "Aadhaar card"},
    ):
        result = build_external_policy(
            extracted,
            document_name="other.pdf",
            owner_demo_user_id="paytm.demo.aarav",
        )
        assert result.record is None
        assert result.added is False
        assert result.decision == "not_policy"
        assert "not identified as an insurance policy" in result.message

    uncertain = build_external_policy(
        {"document_type": "Unknown scanned document"},
        document_name="unknown.pdf",
        owner_demo_user_id="paytm.demo.aarav",
    )
    assert uncertain.record is not None
    assert uncertain.record["verification_status"] == "OCR_EXTRACTED_NEEDS_REVIEW"
    assert uncertain.review_reasons


def test_nominee_requires_owner_action_and_sharing_defaults_off() -> None:
    users = users_as_dicts()
    policy = paytm_policy()
    with pytest.raises(NomineeError, match="confirmation"):
        create_nominee_link(
            policy=policy,
            owner_demo_user_id="paytm.demo.aarav",
            nominee_demo_user_id="paytm.demo.meera",
            relationship="spouse",
            note="",
            owner_confirmed=False,
            share_summary=False,
            users=users,
            existing_links=[],
        )

    link = create_nominee_link(
        policy=policy,
        owner_demo_user_id="paytm.demo.aarav",
        nominee_demo_user_id="paytm.demo.meera",
        relationship="spouse",
        note="Demo note",
        owner_confirmed=True,
        share_summary=False,
        users=users,
        existing_links=[],
    )
    assert link["nominee_acceptance_status"] == "PENDING"
    assert link["demo_link_status"] == "ACTIVE"
    assert link["owner_authorised_summary_sharing"] is False
    assert "Awaiting acceptance" in nominee_status_label(link)
    assert "demo" not in nominee_status_label(link).lower()
    assert "insurer nomination not verified" in nominee_status_label(link).lower()


def test_sharing_defaults_off_and_separate_consent() -> None:
    users = users_as_dicts()
    records = seeded_paytm_records()
    policy = paytm_policy()
    link = create_nominee_link(
        policy=policy,
        owner_demo_user_id="paytm.demo.aarav",
        nominee_demo_user_id="paytm.demo.meera",
        relationship="child",
        note="",
        owner_confirmed=True,
        share_summary=False,
        users=users,
        existing_links=[],
    )
    accepted = respond_to_nominee_link(
        link, nominee_demo_user_id="paytm.demo.meera", accept=True
    )
    assert accepted["nominee_acceptance_status"] == "ACCEPTED"
    assert limited_shared_summary(accepted, records, "paytm.demo.meera") is None

    shared_link = create_nominee_link(
        policy=paytm_policy("demo-pol-aarav-motor-02"),
        owner_demo_user_id="paytm.demo.aarav",
        nominee_demo_user_id="paytm.demo.meera",
        relationship="spouse",
        note="",
        owner_confirmed=True,
        share_summary=True,
        users=users,
        existing_links=[],
    )
    assert limited_shared_summary(shared_link, records, "paytm.demo.meera") is None
    shared_accepted = respond_to_nominee_link(
        shared_link, nominee_demo_user_id="paytm.demo.meera", accept=True
    )
    summary = limited_shared_summary(shared_accepted, records, "paytm.demo.meera")
    assert summary is not None
    assert summary["source_type"] == "NOMINEE_SHARED"
    assert "policy_number_full" not in summary
    assert "premium_amount" not in summary
    assert "policyholder_name" not in summary


def test_nominee_accept_decline_revoke() -> None:
    users = users_as_dicts()
    records = seeded_paytm_records()
    policy = paytm_policy("demo-pol-aarav-life-03")
    link = create_nominee_link(
        policy=policy,
        owner_demo_user_id="paytm.demo.aarav",
        nominee_demo_user_id="paytm.demo.meera",
        relationship="spouse",
        note="",
        owner_confirmed=True,
        share_summary=True,
        users=users,
        existing_links=[],
    )
    accepted = respond_to_nominee_link(
        link, nominee_demo_user_id="paytm.demo.meera", accept=True
    )
    assert link_is_visible_to_nominee(accepted, "paytm.demo.meera") is True
    assert limited_shared_summary(accepted, records, "paytm.demo.meera") is not None

    revoked = revoke_nominee_link(
        accepted, owner_demo_user_id="paytm.demo.aarav"
    )
    assert revoked["demo_link_status"] == "REVOKED"
    assert revoked["nominee_acceptance_status"] == "ACCEPTED"
    assert link_is_visible_to_nominee(revoked, "paytm.demo.meera") is False
    assert limited_shared_summary(revoked, records, "paytm.demo.meera") is None

    declined = respond_to_nominee_link(
        link, nominee_demo_user_id="paytm.demo.meera", accept=False
    )
    assert declined["nominee_acceptance_status"] == "DECLINED"
    assert declined["demo_link_status"] == "REVOKED"
    assert "declined" in nominee_status_label(declined).lower()

    with pytest.raises(NomineeError, match="Only the policy owner"):
        revoke_nominee_link(accepted, owner_demo_user_id="paytm.demo.meera")


def test_reset_demo_restores_fixtures() -> None:
    users = users_as_dicts()
    seed = seeded_nominee_links_as_dicts()
    state = {
        "vs_insurance_active_user_id": "paytm.demo.meera",
        "vs_insurance_section": "nominee",
        "vs_insurance_upload_nonce": 4,
        "vs_insurance_links": [{"link_id": "session-created"}],
        "vs_insurance_external_policies": [{"policy_id": "external-session"}],
        "vs_insurance_nominee_policy_id": "demo-pol-aarav-health-01",
        "vs_other": "keep",
    }
    reset_insurance_session(state, users, seed)
    assert state["vs_insurance_external_policies"] == []
    assert state["vs_insurance_links"] == seed
    assert state["vs_insurance_active_user_id"] == "paytm.demo.aarav"
    assert state["vs_insurance_section"] == "bought"
    assert state["vs_insurance_upload_nonce"] == 0
    assert "vs_insurance_nominee_policy_id" not in state
    assert state["vs_other"] == "keep"


def test_seeded_nominee_link_is_visible_to_meera() -> None:
    records = seeded_paytm_records()
    links = seeded_nominee_links_as_dicts()
    accepted = [
        link
        for link in links
        if link["nominee_acceptance_status"] == "ACCEPTED"
        and link["owner_authorised_summary_sharing"]
    ]
    assert accepted
    summary = limited_shared_summary(accepted[0], records, "paytm.demo.meera")
    assert summary is not None
    assert summary["insurer_name"] == "Suraksha Life Insurance Co."


def test_nominee_status_label_uses_acceptance_not_demo() -> None:
    """nominee_status_label should say 'Awaiting acceptance' not 'Awaiting demo acceptance'."""
    users = users_as_dicts()
    policy = paytm_policy()
    link = create_nominee_link(
        policy=policy,
        owner_demo_user_id="paytm.demo.aarav",
        nominee_demo_user_id="paytm.demo.meera",
        relationship="spouse",
        note="",
        owner_confirmed=True,
        share_summary=False,
        users=users,
        existing_links=[],
    )
    assert "Awaiting acceptance" in nominee_status_label(link)
    assert "demo" not in nominee_status_label(link).lower()


def has_widget(at: AppTest, collection: str, key: str) -> bool:
    try:
        getattr(at, collection)(key=key)
        return True
    except KeyError:
        return False


def has_button(at: AppTest, key: str) -> bool:
    return has_widget(at, "button", key)


def login_at(at: AppTest, login_id: str = "aarav") -> None:
    """Sign in using preset credentials."""
    passwords = {"aarav": "aarav123", "meera": "meera123"}
    password = passwords.get(login_id, "aarav123")
    at.text_input(key="vs_login_id").set_value(login_id)
    at.text_input(key="vs_login_password").set_value(password)
    at.button(key="vs_login_submit").click().run()


def visible_text(at: AppTest) -> str:
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


def test_active_insurances_account_scoped_and_no_user_switch() -> None:
    """Logged-in user sees only their policies; no user switcher; no demo/simulated wording."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    assert not at.exception

    text = visible_text(at)
    # Header prototype label
    assert "Independent hackathon prototype · Paytm-style experience" in text
    assert "No live Paytm connection" in text
    # Section labels - check via radio options
    section_radio = at.radio(key="vs_insurance_section")
    section_labels = [opt for opt in section_radio.options]
    assert "Bought on Paytm" in section_labels
    assert "External Insurance" in section_labels
    assert "Nominee-linked Policies" in section_labels
    # Aarav's policies
    assert "Aarogya" in text
    assert "Drive" in text
    assert "Jeevan" in text
    # Meera's policy should NOT appear
    assert "Yatra" not in text
    # No demo/simulated wording in visible text
    assert "demo" not in text.lower()
    assert "simulated" not in text.lower()
    # No user switcher selectbox
    assert not has_widget(at, "selectbox", "vs_insurance_active_user_id")
    # Profile shows in header area (logout button present)
    assert has_button(at, "vs_logout")


def test_active_insurances_switch_user_via_logout_login() -> None:
    """Switching accounts is done via logout/login, not a user switcher."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    assert not at.exception
    text = visible_text(at)
    assert "Aarogya" in text
    assert "Yatra" not in text

    # Logout
    at.button(key="vs_logout").click().run()
    assert not at.exception
    assert at.session_state["vs_auth_user_id"] is None

    # Login as Meera
    login_at(at, "meera")
    at.button(key="vs_nav_insurance").click().run()
    assert not at.exception
    text = visible_text(at)
    assert "Yatra" in text
    assert "Aarogya" not in text
    assert "Drive" not in text
    assert "Jeevan" not in text


def test_external_insurance_shows_disclosure_and_upload_controls() -> None:
    """External section shows the Sarvam disclosure and upload controls."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    at.radio(key="vs_insurance_section").set_value("external").run()
    assert not at.exception

    text = visible_text(at)
    assert "Add an external policy document" in text
    assert "Sarvam AI Document AI" in text
    assert "authorised to share" in text
    # Upload controls present
    assert at.file_uploader(key="vs_insurance_upload_0")
    assert at.checkbox(key="vs_insurance_upload_ack_0")


def test_nominee_section_shows_limited_summary_for_meera() -> None:
    """Meera sees the seeded accepted sharing link with limited summary."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "meera")
    at.button(key="vs_nav_insurance").click().run()
    at.radio(key="vs_insurance_section").set_value("nominee").run()
    assert not at.exception

    text = visible_text(at)
    assert "Limited summary" in text
    assert "Insurer nomination not verified" in text
    assert "Shared by" in text
    assert "Aarav Sharma" in text
    assert "Jeevan" in text
    assert "demo" not in text.lower()


def test_policy_document_viewer_tab_and_download() -> None:
    """Each policy card has Summary and Policy document tabs; download buttons exist."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    assert not at.exception

    # Check that download buttons for policy documents exist
    download_buttons = [d for d in at.download_button if "vs_download_policy_doc_" in d.key]
    assert len(download_buttons) >= 3  # Aarav has 3 seeded policies
    # Verify keys match expected pattern
    policy_ids = [db.key.replace("vs_download_policy_doc_", "") for db in download_buttons]
    assert "demo-pol-aarav-health-01" in policy_ids
    assert "demo-pol-aarav-motor-02" in policy_ids
    assert "demo-pol-aarav-life-03" in policy_ids

    # Tabs should be present (Summary, Policy document)
    tab_labels = [t.label for t in at.tabs]
    assert "Summary" in tab_labels
    assert "Policy document" in tab_labels


def test_logout_preserves_external_policies_and_nominee_links() -> None:
    """Policy records and nominee links persist across logout/login."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    # Verify seeded policies present
    text = visible_text(at)
    assert "Aarogya" in text

    # Logout
    at.button(key="vs_logout").click().run()
    assert at.session_state["vs_auth_user_id"] is None

    # Login again as Aarav
    login_at(at, "aarav")
    at.button(key="vs_nav_insurance").click().run()
    text = visible_text(at)
    assert "Aarogya" in text

    # Links preserved (seeded link)
    at.radio(key="vs_insurance_section").set_value("nominee").run()
    text = visible_text(at)
    assert "Sharing links you created" in text
    assert "Insurer nomination not verified" in text


# ===== Phase 2 Update: Nominee 360 tests =====

def test_nominee_consistency_name_normalisation() -> None:
    """Test name normalisation for comparison."""
    from src.nominee_consistency import normalise_name_for_comparison, name_similarity

    assert normalise_name_for_comparison("MEERA R SHARMA") == "meera r sharma"
    assert normalise_name_for_comparison("Meera Sharma") == "meera sharma"
    assert normalise_name_for_comparison("  MEERA  SHARMA  ") == "meera sharma"
    # Similarity should be high for variations
    score = name_similarity("MEERA R SHARMA", "Meera Sharma")
    assert score >= 0.9


def test_nominee_consistency_dob_parsing() -> None:
    """Test DOB parsing and age calculation."""
    from src.nominee_consistency import parse_dob, calculate_age
    from datetime import date

    assert parse_dob("1991-04-12") == date(1991, 4, 12)
    assert parse_dob("12-04-1991") == date(1991, 4, 12)
    assert parse_dob("12/04/1991") == date(1991, 4, 12)
    assert parse_dob("12.04.1991") == date(1991, 4, 12)
    assert parse_dob("invalid") is None

    # Age calculation
    dob = date(1991, 4, 12)
    event = date(2026, 10, 1)
    assert calculate_age(dob, event) == 35


def test_nominee_consistency_minor_flag_life_policy() -> None:
    """Test minor nominee flag on life policy with missing appointee."""
    from src.nominee_consistency import check_minor_nominee
    from datetime import date

    # Minor at event date, no appointee -> review flag
    code = check_minor_nominee("2012-03-04", date(2026, 10, 1), "life", None, None)
    assert code == "MINOR_NOMINEE_APPOINTEE_REVIEW"

    # Minor but appointee present -> unverified
    code = check_minor_nominee("2012-03-04", date(2026, 10, 1), "life", "Guardian Name", "Father")
    assert code == "APPOINTEE_DETAILS_UNVERIFIED"

    # Adult -> no flag
    code = check_minor_nominee("1991-04-12", date(2026, 10, 1), "life", None, None)
    assert code is None

    # Non-life product -> product rule confirmation required
    code = check_minor_nominee("2012-03-04", date(2026, 10, 1), "health", None, None)
    assert code == "PRODUCT_RULE_CONFIRMATION_REQUIRED"


def test_nominee_consistency_analyse_portfolio() -> None:
    """Test full portfolio analysis for Aarav's policies."""
    from src.nominee_consistency import analyse_portfolio, load_linked_profiles
    from datetime import date

    profiles = load_linked_profiles()
    # Load seeded nominee links
    from src.mock_paytm_data import seeded_nominee_links_as_dicts
    links = seeded_nominee_links_as_dicts()

    findings, summary = analyse_portfolio(
        owner_demo_user_id="paytm.demo.aarav",
        event_date=date(2026, 10, 1),
        linked_profiles=profiles,
        nominee_links=links,
    )

    assert summary["total_policies"] == 3
    assert summary["total_findings"] >= 3  # At least insurer registration flags
    # Check insurer registration flags exist
    reg_findings = [f for f in findings if f.finding_code == "INSURER_REGISTRATION_NOT_CONFIRMED"]
    assert len(reg_findings) == 3


def test_nominee_360_ui_loads() -> None:
    """Test Nominee 360 page loads without errors."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_nominee360").click().run()
    assert not at.exception
    assert at.button(key="vs_nom360_analyse")


def test_nominee_360_analysis_runs() -> None:
    """Test Nominee 360 analysis produces findings."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_nominee360").click().run()
    at.button(key="vs_nom360_analyse").click().run()
    assert not at.exception
    assert "vs_nom360_findings" in at.session_state
    findings = at.session_state["vs_nom360_findings"]
    assert len(findings) >= 3
    summary = at.session_state["vs_nom360_summary"]
    assert summary["total_policies"] == 3


# ===== Phase 2 Update: Chatbot tests =====

def test_chatbot_ui_loads() -> None:
    """Test AI Assistant chatbot page loads."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    login_at(at, "aarav")
    at.button(key="vs_nav_chatbot").click().run()
    assert not at.exception
    # Check for chat input
    assert has_widget(at, "chat_input", "vs_chatbot_input") or has_widget(at, "text_input", "vs_chatbot_input")


def test_chatbot_context_builds() -> None:
    """Test chatbot context builds policy and finding info."""
    from src.chatbot_ui import _build_policy_context
    from datetime import date

    # Test with Aarav's user ID
    policy_details, policy_count, finding_count, finding_summary = _build_policy_context("paytm.demo.aarav")
    assert policy_count == 3
    assert "Aarogya" in policy_details
    assert "Jeevan" in policy_details
    assert "Drive" in policy_details


def test_chatbot_nemotron_call_structure() -> None:
    """Test Nemotron call uses correct model and endpoint."""
    import os
    assert os.environ.get("LLM_105B_MODEL") == "nvidia/nemotron-3-ultra-550b-a55b"
    assert os.environ.get("LLM_105B_BASE_URL") == "https://openrouter.ai/api/v1"
