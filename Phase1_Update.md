Virasat Saathi — Phase 2 OpenCode Update
Purpose: Extend the already-working Phase 1 application with an Active Insurances area.

Build target: A functional local prototype for an 8-hour hackathon. Paytm-related functionality is simulated with a Paytm-inspired interface and seeded demo data. Sarvam Document AI is the only live external integration in this phase.

Product line: Financial guidance when you need it. Support when it matters most.
0. Instructions to OpenCode
Read this file and inspect the existing repository before changing anything.
- Do not rebuild Phase 1. Preserve the existing Claims Companion and Family Finance Finder flows, routes, components, styling and tests. Make the smallest additive changes needed.
- Build the new Active Insurances experience described below.
- Paytm is mock-only. Do not call Paytm APIs, use Paytm SDKs, request Paytm credentials, process payments or implement real authentication. Use a clearly labelled demo Paytm session and local seeded data.
- Sarvam Document AI must be a real integration when SARVAM_API_KEY is configured. Do not fake a successful OCR response. When the key is absent or the API fails, show a clear error and keep the seeded demo policies available.
- Never hardcode or print API keys. Read the Sarvam key from .env; commit only .env.example.
- Keep the application runnable throughout. Implement and test one vertical slice at a time.
- At completion, provide changed files, exact setup/run/test commands, required environment variables, known limitations and a short demo script.
1. Phase 2 user experience
Add a new navigation item: Active Insurances.

On opening it, show a Paytm-inspired, mobile-friendly dashboard with three clear sections/tabs:
1. Bought on Paytm — policies attached to the currently selected mock Paytm user.
2. External Insurance — documents uploaded by the user and processed using Sarvam Document AI.
3. Nominee-linked Policies — policies whose owner has created a mock Paytm-ID nominee link to the currently selected demo user and explicitly allowed the limited summary to be shared.
Also provide a Manage Nominees action from each eligible policy card in the first two sections.
Visual treatment
- Use a familiar Indian consumer-fintech layout: blue/white palette, compact top bar, clean cards, rounded controls, clear navigation and strong mobile responsiveness.
- Add a persistent label: “Independent hackathon prototype · Paytm-style demo · No live Paytm connection”.
- Do not use Paytm's logo, official assets or language that implies this is an official Paytm feature. The supplied Paytm developer documentation is a future reference only; it must not be integrated in this phase.
- Keep the existing Virasat Saathi identity visible.
- Every seeded Paytm policy, account identity, nominee lookup and insurer acknowledgement must show a DEMO or SIMULATED label.
2. Section A — Bought on Paytm (mock data)
Create a local mock Paytm session with a user switcher. Seed at least two fictional users so nominee flows can be demonstrated by switching accounts.

Use fake identifiers such as paytm.demo.aarav and paytm.demo.meera; do not use real phone numbers, email addresses or personal identifiers.

Seed at least two mock policies for the default demo user, covering two product types (for example, health and motor). Each card should display:
- Insurer name (fictional or clearly marked demo data)
- Product / insurance type
- Masked policy number
- Policy period
- Sum insured / coverage, if present in fixture
- Premium and frequency, if present in fixture
- Source: Bought on Paytm — DEMO
- Status: Demo record — not verified with insurer
- View details and Manage nominee actions
The demo user switcher should simulate logging in as another Paytm user. It is not authentication and must never collect credentials or OTPs.
Required files/data
Add data/mock_paytm_users.json and data/mock_paytm_policies.json (or equivalent fixtures consistent with the existing project).

Every mock policy must have a stable internal ID, owner_demo_user_id, product type, masked policy number, dates, display fields, source_type: PAYTM_DEMO and verification_status: SIMULATED_NOT_VERIFIED.
3. Section B — External Insurance (real Sarvam OCR)
Allow the user to upload an externally purchased insurance policy document and process it with Sarvam Document AI Extract.
Supported upload scope
- Accept PDF, PNG, JPG and JPEG only.
- Apply an application-level maximum of 10 MB and 20 PDF pages for the hackathon, even though the provider may permit larger files.
- Reject empty, unsupported, over-limit or unreadable files with a clear message.
- Do not support ZIP/TIFF in this phase.
- Do not store the uploaded original file permanently. Keep it in memory for the request, then release the buffer after processing. Do not write it to logs, cache, analytics or the repository.
Before upload, show a required acknowledgement:
“This document may contain personal, financial or health information. If you continue, the selected file will be transmitted to Sarvam AI Document AI for extraction. Do not upload a document unless you are authorised to share it. Review the provider's applicable data handling terms before using real customer documents.”

The checkbox must be unchecked by default. Do not call Sarvam until the user has acknowledged it and clicked Process document.
Sarvam implementation
Use the current Sarvam Document AI SDK/API, not the legacy Document Digitization job API and not a chat-completions endpoint.

Official references:
- Overview: https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/overview
- Extract guide: https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/how-to/extract
- Supported formats and limits: https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/languages-formats-limits
Install the current Python SDK using pip install -U sarvamai and initialise it with SARVAM_API_KEY from the environment. The documented Python pattern is:
import json
import os
from sarvamai import SarvamAI

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])

schema = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "description": "Document type; identify whether this is an insurance policy document"},
        "insurer_name": {"type": "string", "description": "Name of the insurance company, as printed"},
        "product_name": {"type": "string", "description": "Insurance product or plan name, as printed"},
        "policyholder_name": {"type": "string", "description": "Name of policyholder, as printed"},
        "insured_persons": {"type": "string", "description": "Names of insured persons, if explicitly printed"},
        "policy_number": {"type": "string", "description": "Policy number, preserve exact characters"},
        "uin": {"type": "string", "description": "Insurance product UIN, if printed"},
        "policy_start_date": {"type": "string", "description": "Policy start date exactly as printed"},
        "policy_end_date": {"type": "string", "description": "Policy end date exactly as printed"},
        "sum_insured": {"type": "string", "description": "Sum insured / coverage amount exactly as printed, including currency"},
        "premium_amount": {"type": "string", "description": "Premium amount exactly as printed, including currency"},
        "premium_frequency": {"type": "string", "description": "Payment frequency, only if printed"},
        "nominee_name": {"type": "string", "description": "Nominee name, if printed"},
        "nominee_relationship": {"type": "string", "description": "Nominee relationship, if printed"}
    }
}

job = client.doc_ai.extract(
    file=[(filename, file_object, mime_type)],
    schema=json.dumps(schema),
    language="en-IN",
    output_format="json",
)
Follow the documented asynchronous job lifecycle:
1. Submit client.doc_ai.extract(...) and retain the returned job_id in memory.
2. Poll client.doc_ai.get_status(job_id=job.job_id) every few seconds, with an overall application timeout (suggested: 120 seconds).
3. Treat completed and partially_completed as result-bearing states; treat failed and rejected as errors.
4. Retrieve structured values using client.doc_ai.get_results(job_id=job.job_id).
5. Normalise the SDK response into the application's internal policy schema. Do not assume undocumented response fields; inspect the installed SDK response and handle both object/dict forms where practical.
Use language="en-IN" as the default. Add a simple language selector for en-IN, hi-IN and bn-IN only if it can be completed without delaying the core flow. The API supports 22 Indian languages plus English; do not attempt to expose all languages in this phase.
Environment variables
Add these to .env.example:
SARVAM_API_KEY=
SARVAM_ENABLED=true
SARVAM_DOCUMENT_LANGUAGE=en-IN
SARVAM_JOB_TIMEOUT_SECONDS=120
If SARVAM_API_KEY is missing, disable live upload processing and show Add SARVAM_API_KEY to .env to enable document extraction. Do not silently return mock OCR data.
Extracted policy fields
At minimum, attempt to extract:
- document type
- insurer name
- product name / insurance type
- policyholder name
- insured person(s)
- policy number
- UIN, if available
- policy start and end dates
- sum insured / coverage amount
- premium and frequency
- nominee name and relationship, if printed
Missing values must stay Not found in document; never infer or fabricate them. Preserve the raw extracted value for review but mask policy numbers in summary cards. Avoid showing full policy number after save; reveal only on a deliberate detail action if needed.
Automatic inventory insertion and review
After a successful Sarvam response:
1. Create an external-policy inventory record automatically in session state.
2. Set source_type: EXTERNAL_DOCUMENT and verification_status: OCR_EXTRACTED_NEEDS_REVIEW.
3. Display the new record immediately under External Insurance with a Review extracted details action.
4. Let the user correct fields and confirm that the document is theirs / they are authorised to add it.
5. After user confirmation, set verification_status: USER_REVIEWED_UNVERIFIED — not insurer-verified or confirmed active.
6. Derive a display hint from dates only, e.g. Date window appears current; insurer status not checked. Do not label it Active based only on OCR or dates.
If the document is clearly not an insurance policy, do not add it as an insurance record. Show This document was not identified as an insurance policy. No policy was added. If document type is uncertain or essential fields are missing, add it to a Needs review queue rather than discarding the result.

Never make claim eligibility, policy validity, coverage, exclusion, premium-paid or current-active conclusions from OCR alone.
4. Section C — Nominee-linked policies (mock Paytm-ID integration)
This phase must demonstrate the journey without connecting to Paytm or an insurer.
Manage nominee from a policy
For every mock Paytm policy and every user-confirmed external policy, show Manage nominee. The form should:
1. Select a nominee from a seeded mock Paytm directory using a demo Paytm ID (for example paytm.demo.meera).
2. Display the matched fictional profile and ask the policyholder to verify it.
3. Capture relationship (spouse, child, parent, other) and a short optional note.
4. Capture explicit owner consent to create the simulated nominee link.
5. Separately ask whether the owner wants to share a limited policy summary with the nominee. Default this to off. Do not treat nomination as permission to disclose the complete policy document.
6. Save a mock request with status DEMO_REQUESTED or AWAITING_DEMO_ACCEPTANCE.
For the hackathon, a single nominee per policy is sufficient. Do not implement percentage splits or complex legal nomination rules.
Simulate acceptance and nominee view
- Provide a clearly labelled demo user switcher (e.g. Aarav Demo / Meera Demo) to simulate changing Paytm users.
- When switching to the intended nominee, show a pending nominee invitation in a Nominee-linked Policies area.
- Allow the nominee to Accept demo link or Decline demo link.
- After acceptance, show only the limited summary the policyholder explicitly allowed. Do not reveal full policy documents or sensitive fields by default.
- The owner can revoke the demo sharing link. This is not an insurer nomination cancellation.
- Seed at least one completed mock nominee link so the third dashboard section is visible immediately during the demo.
Mandatory wording / legal boundary
Show this text on the nominee form and status view:
“This creates a simulated Paytm-ID family link inside the hackathon prototype. It does not register, change or confirm a legal nominee with the insurer. To make or change a legally effective nomination, use the insurer's official process and obtain its acknowledgement.”

Use labels such as:
- Demo nominee selected
- Awaiting demo acceptance
- Demo link accepted
- Insurer nomination not verified
Never display Nominee registered unless a real insurer confirmation exists (there is no such integration in this phase).

Keep nominee identity linking and policy-summary sharing as separate consent decisions. A person must not see another user's policy merely because they were selected as nominee.
5. Shared policy data model
Use a common normalised policy object for the three sections. Adapt names to existing code, but include equivalent fields:
{
    "policy_id": "stable internal UUID",
    "source_type": "PAYTM_DEMO | EXTERNAL_DOCUMENT | NOMINEE_SHARED",
    "owner_demo_user_id": "demo user id or null when not applicable",
    "insurer_name": "string or null",
    "product_name": "string or null",
    "product_type": "health | life | motor | travel | other | unknown",
    "policy_number_masked": "string or null",
    "policy_number_full": "session-only value if needed; never log",
    "uin": "string or null",
    "policy_start_date": "ISO date or null",
    "policy_end_date": "ISO date or null",
    "sum_insured": "string or null",
    "premium_amount": "string or null",
    "premium_frequency": "string or null",
    "policyholder_name": "string or null",
    "insured_persons": [],
    "ocr_nominee_name": "string or null",
    "ocr_nominee_relationship": "string or null",
    "verification_status": "SIMULATED_NOT_VERIFIED | OCR_EXTRACTED_NEEDS_REVIEW | USER_REVIEWED_UNVERIFIED",
    "display_status": "derived label; never inferred insurer-active status",
    "created_at": "ISO timestamp",
    "document_name": "filename only, optional; do not store file bytes"
}
Create separate NomineeLink data with:
- link_id
- policy_id
- owner_demo_user_id
- nominee_demo_user_id
- relationship
- owner_authorised_summary_sharing (boolean)
- nominee_acceptance_status (PENDING, ACCEPTED, DECLINED)
- demo_link_status (ACTIVE, REVOKED)
- timestamps
The nominee link is demo data and is not a legal insurance nomination record.
6. Suggested additive project structure
Preserve the current application structure. Add or adapt only the modules needed:
app.py                         # existing app; add Active Insurances navigation
src/
  insurance_inventory.py       # merge, filter and display normalised policy records
  sarvam_document_ai.py        # real Sarvam Document AI adapter
  policy_extraction_schema.py  # field schema sent to Sarvam
  nominee_demo.py              # mock Paytm-ID lookup, invite, accept, revoke
  mock_paytm_data.py           # seeded users and purchased policies
  upload_validation.py         # MIME, extension, size and page checks
  policy_normalizer.py         # convert Sarvam output to common policy object
  ... existing Phase 1 modules remain unchanged

data/
  mock_paytm_users.json
  mock_paytm_policies.json
  mock_nominee_links.json
  ... existing Phase 1 fixtures remain unchanged
Do not create duplicate modules if the repository already has equivalent functionality. Reuse the existing session-state, styling, translations and navigation patterns.
7. Privacy, security and safe handling
- Use synthetic records for Paytm users, Paytm-purchased policies and nominee relationships.
- Never call Paytm APIs or request Paytm secrets in this phase.
- Do not request OTP, UPI PIN, password, Aadhaar, PAN or real Paytm login credentials.
- The Sarvam API key stays server-side in .env; never expose it to frontend JavaScript or UI.
- Before transmitting a user-selected document to Sarvam, show the upload disclosure and require an unchecked-by-default consent checkbox plus an explicit Process action.
- Do not log file contents, OCR result contents, full policy number, policyholder name or API key.
- Do not persist uploaded documents. Do not cache OCR results across sessions unless the existing app already has an explicitly approved secure store; the default is session-only storage.
- Provide Remove document / policy from this session and Reset demo actions.
- Use only test/synthetic or documents the uploader is authorised to share for the hackathon. Production use requires provider data-processing/retention review, Paytm approval and appropriate privacy/legal review. Do not claim this prototype is certified compliant.
- Treat OCR as fallible. Show missing fields clearly and require user review. OCR does not authenticate a policy or prove it is in force.
- Do not expose nominee-linked policy details until owner-authorised summary sharing is true and the invited demo user has accepted.
- Do not enable claim filing, payments, policy cancellation or legal nominee registration in Phase 2.
8. Tests and acceptance criteria
P0 — Phase 2 is complete only when all pass
1. Existing Phase 1 Claims Companion and Family Finance Finder still run unchanged.
2. Active Insurances navigation opens a working dashboard with all three sections.
3. Bought on Paytm shows seeded policies for the currently selected mock user and clearly labels them simulated.
4. Switching demo users changes the policy/nominee view correctly; no real authentication is requested.
5. Upload accepts valid PDF/JPG/JPEG/PNG files within the app limits and rejects unsupported/oversized files.
6. Without SARVAM_API_KEY, the app explains how to configure the key and does not pretend OCR succeeded.
7. With a valid key, Sarvam Document AI Extract is called using the current sarvamai SDK; job status is polled and structured results are retrieved.
8. Sarvam API errors, timeouts, rejected documents and partially completed results are handled without crashing the app.
9. A successful extraction automatically creates an External Insurance record with OCR_EXTRACTED_NEEDS_REVIEW status.
10. Missing OCR fields remain blank / Not found in document; no values are fabricated.
11. User review can edit extracted values and mark the record reviewed, but the UI still says insurer status is unverified.
12. A non-insurance document is not silently added as a policy.
13. Manage Nominee can find a user only in the seeded mock Paytm directory.
14. Nominee link creation requires owner action; sharing policy details is a separate opt-in and defaults off.
15. The nominated demo user can accept/decline; only accepted, explicitly shared limited summaries appear in their dashboard.
16. Revoking a demo link removes the limited summary from the nominee view.
17. Every nominee status is explicitly marked DEMO and says insurer registration has not happened.
18. Reset demo clears session-created external policy records and nominee changes and restores fixtures.
19. No Paytm network/API call exists in the code path.
20. No API key, uploaded file bytes or sensitive extracted values are written to logs or committed files.
Minimum tests
- test_mock_paytm_user_switch — active policy list filters by demo user.
- test_no_paytm_network_calls — ensure Paytm integration is mock-only.
- test_upload_file_type_and_size — permitted files pass; others fail.
- test_sarvam_missing_key — clear disabled-state, no false success.
- test_sarvam_extract_job_lifecycle — mocked SDK pending → completed → results.
- test_sarvam_timeout_and_failure — actionable error, no crash.
- test_extraction_missing_fields_not_invented — absent values remain null/unknown.
- test_ocr_record_created_needs_review — success adds the external policy automatically with correct status.
- test_non_policy_document_not_added — uncertain/non-policy document goes to review/error, not active inventory.
- test_nominee_requires_owner_action — no link created without explicit owner confirmation.
- test_sharing_defaults_off — nominee cannot see details until sharing is enabled and accepted.
- test_nominee_accept_decline_revoke — state transitions and visibility are correct.
- test_reset_demo — resets all Phase 2 session state.
9. Implementation order (8-hour hackathon)
0:00–0:30 — Inspect and preserve Phase 1
- Run the existing app and tests first.
- Identify current framework, routing, session state, styling and data structures.
- Create a Git checkpoint/branch before edits.
0:30–1:45 — Active Insurances UI + mock Paytm data
- Add navigation and three tabs/sections.
- Implement mock Paytm user switcher and seeded Paytm policies.
- Make the UI visually Paytm-inspired but clearly simulated.
1:45–3:45 — Sarvam Document AI integration
- Add .env.example and SDK dependency.
- Implement upload validation and disclosure/consent.
- Implement Extract → poll → get results using current SDK.
- Normalise fields, create external inventory item automatically and show review screen.
- Test missing key and API failure paths.
3:45–5:15 — Nominee demo workflow
- Implement mock Paytm-ID lookup from local fixture.
- Add nominee form, owner confirmation and separate sharing opt-in.
- Add demo user switcher acceptance/decline and limited nominee view.
- Add revoke action and legal disclaimer.
5:15–6:15 — Integrate and regression test
- Verify all three insurance sections.
- Run Phase 1 tests and Phase 2 tests.
- Fix regressions and session-state issues.
6:15–7:15 — UI and error-state polish
- Loading/progress for OCR job lifecycle.
- Empty states, success/error messages, field review and mobile layout.
- Ensure there are no inert controls or fake live status indicators.
7:15–8:00 — Freeze and rehearse
- Test with a synthetic sample PDF/image and a real Sarvam key if available.
- Test the no-key fallback.
- Reset demo and rehearse the flow below.
If the real Sarvam key is not available during the hackathon, finish the adapter, unit-test the job lifecycle with a mocked SDK client, clearly disable live OCR in the UI, and demonstrate the rest using seeded external-policy fixtures. Do not label mocked extraction as real Sarvam OCR.
10. Demo sequence (2–3 minutes)
1. Open Active Insurances. Show the Paytm-style demo session and two Bought on Paytm policies.
2. Open one policy and add a nominee using paytm.demo.meera. Enable limited summary sharing and submit the simulated link.
3. Switch to Meera Demo. Show the pending invitation, accept it and show the limited policy summary under Nominee-linked Policies.
4. Switch back to the owner and show that the link is a demo workflow, not insurer registration.
5. Upload a synthetic external policy PDF. Show Sarvam processing, the extracted fields and automatic creation of an External Insurance record marked Needs review.
6. Correct one field, confirm the record and point out that it remains Insurer status not verified.
7. End by showing all three sections and the clear boundary between Paytm mock data, Sarvam OCR output and insurer-confirmed information.
11. API and documentation notes
Paytm
The supplied reference, https://www.paytmpayments.com/docs, is Paytm for Developers documentation focused on merchant/payment products such as Payment Gateway, QR, payment links, subscriptions, refunds and settlements. It is not being used as a customer-login or insurance-policy API in this phase. No Paytm API is required for this prototype. Use local mock data and a Paytm-inspired UI only.
Sarvam
Current Sarvam Document AI docs identify Extract as schema-based extraction at POST /doc-ai/v1/job/extract, using the sarvamai SDK, asynchronous job status polling and get_results(). Extract supports PDF up to 20 pages and PDF/PNG/JPG/JPEG; the app intentionally applies smaller limits for a quick, safer demo. Do not use the legacy document_intelligence API for new implementation.

Source references:
- https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/overview
- https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/how-to/extract
- https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/languages-formats-limits