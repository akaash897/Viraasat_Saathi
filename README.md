# Virasat Saathi

**Financial guidance when you need it. Support when it matters most.**

Virasat Saathi is an independent, local-first hackathon prototype with three financial-guidance journeys:

1. **Claims Companion** — helps a living policyholder understand a *fictional* sample health-insurance policy, prepare a reimbursement checklist, see which document categories are still unmarked, draft a follow-up, and track next steps.
2. **Family Finance Finder** — reads a *synthetic* transaction statement, finds possible insurance / investment / loan / recurring-payment clues, shows the exact rows behind each lead, and routes the user to official channels for verification.
3. **Active Insurances (Phase 2)** — a Paytm-style *demo* inventory of seeded policies, an external-policy upload path that uses **real Sarvam Document AI Extract** when configured, and an explicitly consented **simulated** nominee-link workflow with limited summary sharing.

All journeys share an evidence-first case panel, clear source labels and session-only state. The product rule is:

> **AI explains and assists. Deterministic rules check. Official sources establish requirements. The user decides.**

This is **not** an insurer, broker, TPA, lawyer, doctor, surveyor, claims decision-maker, investment adviser or legal-heir determination service. It does **not** decide coverage, eligibility, claim approval or settlement, and it does **not** guarantee payment. It has **no** live Paytm, bank, insurer, UPI-mandate, government-portal or Sarvam dependency in the default demo.

---

## 1. Prototype disclaimer and prohibited real-data notice

- This is an **independent hackathon prototype**. It is not affiliated with Paytm, any insurer, IRDAI, RBI, SEBI, IEPFA, the Council for Insurance Ombudsmen or Sarvam AI.
- It is **not a legal opinion** and is **not certified as compliant** with any law or regulation. A real launch would need partner approval, security review, a privacy notice, contracts and Indian legal/regulatory review.
- **Use the fictional demo case.** Do not upload real medical, insurance, banking or deceased-person records.
- Real-data processing is **disabled/not approved** for any public demo. The local upload path exists only as a local-only, in-memory convenience for synthetic testing.
- Do not deploy this upload path to a public URL.
- The app does not request or process names, Aadhaar, PAN, bank account numbers, policy numbers, claim numbers, phone numbers, UPI IDs, OTPs, passwords, UPI PINs, exact medical diagnoses or beneficiary details.

The app shows a persistent banner:

> Hackathon prototype — use the fictional demo case. Do not upload real medical, insurance, banking or deceased-person records.

---

## 2. What works (implemented features)

### Claims Companion

- Loads the fictional case `DEMO-CLAIM-001` and the fictional policy `Virasat Sample Health Policy — DEMO ONLY`.
- Shows policy facts with **clause ID and page citations** from `data/demo_policy.json`.
- Provides a deterministic topic lookup. If a topic is not in the fixture, it says **“Not verified in the available information”** and links the official insurer/regulator route.
- Shows a 7-category document checklist from `data/demo_claim.json`.
- Neutral checklist statuses: **Not marked**, **Marked provided**, **Need to confirm with insurer**.
- Calculates the remaining unmarked count deterministically. Marking an item means only that the user marked it provided; it never implies insurer validation, authenticity, sufficiency or acceptance.
- Shows “Why this is listed” with the exact checklist/policy source ID.
- Generates four editable, deterministic draft types:
  - missing-document follow-up,
  - claim-status request,
  - response to a request for more information,
  - insurer-grievance preparation.
- Drafts use only fictional case fields and checklist category names. There is no email, WhatsApp, insurer API or portal submission. A review checkbox must be ticked before the `.txt` download is enabled.
- Session-only tracker with user-entered reminder dates, notes and “Mark done”.
- Escalation help with official GRO, Bima Bharosa and Ombudsman links.
- Anti-fraud warning: never pay a fee to release a claim, never scan a QR code from a stranger, never share an OTP / UPI PIN / password / card PIN.
- Downloadable **DEMO**-watermarked case summary.
- Optional local-only PDF/TXT readability check. No OCR; scanned PDFs get a plain “OCR is not supported” message. No authenticity, sufficiency, coverage or eligibility conclusion.

### Family Finance Finder

- Loads the included synthetic statement `data/demo_transactions.csv` (9 rows).
- Detects four configured lead categories from the demo:
  - possible insurance payment,
  - possible investment or SIP,
  - possible lender or EMI,
  - possible recurring subscription.
- Uses a small, explicit keyword dictionary in `src/transaction_matcher.py`.
- Recurrence requires matching transactions in **at least two distinct calendar months**. A single row is labelled a **single clue** with **low** strength. Multiple rows in the same month do **not** satisfy monthly recurrence.
- Every lead shows:
  - the category,
  - pattern strength (rule-based heuristic only),
  - the exact source rows (row number, date, description, amount, direction),
  - the rule that detected it,
  - what it does **not** prove,
  - a suggested next step,
  - relevant official links where they exist.
- Every result says it is a **lead** and requires institutional confirmation. It never infers a balance, coverage amount, units held, outstanding principal, beneficiary, ownership or claim eligibility.
- Optional local-only CSV upload with an acknowledgement gate, 10 MB cap, in-memory parsing and no model calls.
- Session-only case note and next-step checklist.
- Links to the Common Landing Portal, RBI UDGAM, Bima Bharosa, IEPFA and SEBI investor guidance **only when relevant**. The UI explicitly says: **“We have not searched this portal; open it to verify the lead.”**

### Active Insurances (Phase 2, additive)

- **Login / Logout with preset credentials.** The app opens at a sign-in screen with two prototype accounts (Aarav Sharma / aarav123, Meera Sharma / meera123). After signing in, the top-right header shows the signed-in profile with a **Log out** button. No Paytm API, SDK, credential, OTP, UPI PIN or real authentication exists anywhere in this path.
- **Bought on Paytm.** Seeded fictional users (`paytm.demo.aarav`, `paytm.demo.meera`) and four clearly fictional policies across health, motor, life and travel. The inventory is scoped to the signed-in account; switching accounts is done by logging out and back in. The UI carries a persistent **“Independent hackathon prototype · Paytm-style experience · No live Paytm connection”** label.
- **Policy document viewer.** Every policy card has **Summary** and **Policy document** tabs. The document tab renders a generated PDF (seeded policies) or the uploaded file bytes (external policies) with a download button. Files are held in memory for the session and are never written to disk.
- **External Insurance (real Sarvam Document AI when configured).** PDF, PNG, JPG and JPEG only; 10 MB maximum; 20 PDF pages maximum; ZIP and TIFF rejected by extension and magic-byte checks. The exact upload disclosure is shown before the file picker. The consent checkbox is unchecked by default, and no Sarvam call happens until it is ticked and **Process document** is pressed. Files are held in memory for the request and are never written to disk.
- **Sarvam Extract lifecycle.** The adapter submits `client.doc_ai.extract`, polls `get_status` to `completed` / `partially_completed` / `failed` / `rejected`, then reads `get_results`. A missing key, disabled flag, timeout, rejected document, unreadable response or SDK/network error produces a visible error and leaves the seeded policies available. It never fabricates OCR success.
- **Review queue, not verification.** A successful extraction creates a session-only record with status `OCR_EXTRACTED_NEEDS_REVIEW`. Missing fields stay **Not found in document**. Incomplete or uncertain insurance results also go to Needs review. Clearly non-insurance documents (for example a bank statement, Aadhaar card or invoice) are not added. Only an explicit user review with an authorisation checkbox changes the status to `USER_REVIEWED_UNVERIFIED`; this still does **not** verify the policy with the insurer or prove it is active.
- **Nominee-linked Policies (family-sharing links).** The nominee must be chosen from the seeded directory and only after the owner ticks a confirmation checkbox. Summary sharing is a separate checkbox and is **off by default**. The nominee can accept or decline; the owner can revoke. Policy details are shown only after acceptance **and** explicit owner-authorised sharing, and then only as a limited summary (masked policy number; no full document, premium or full policy number). Every screen says **“Insurer nomination not verified”** and explains that this is not a legal nomination.
- **No reset.** The **Reset insurance demo** button has been removed. Session state for policies and nominee links persists across logout/login so the nominee flow can be demonstrated by switching accounts.

### Shared

- English-only UI (Hindi toggle removed). Reviewed static strings for key labels, instructions, status wording, fallbacks and all safety-critical disclaimers.
- Calm off-white / navy / teal / restrained saffron visual theme.
- Persistent “Independent hackathon prototype · Synthetic data” label.
- **Sources & limitations** expander listing every official link and what the prototype cannot verify.
- Optional Sarvam AI paraphrase for fictional checklist content only. The app works fully with no API key and no internet access.

---

## 3. Requirements and exact setup

### Runtime

- Python **3.11+** (tested here with Python **3.14.6** on Windows).
- `pip`.
- No database, cloud account or internet connection is required for the default demo.
- Optional internet only if you deliberately enable Sarvam. Sarvam Document AI (Phase 2) requires a real `SARVAM_API_KEY` and `SARVAM_ENABLED=true`; without them the upload control stays disabled and the seeded policies remain available.

### Windows PowerShell (exact commands)

```powershell
cd D:\Virasaat_Saathi\Viraasat_Saathi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use the virtual environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux (exact commands)

```bash
cd /path/to/Viraasat_Saathi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** if the browser does not open automatically.

### Test command

With the virtual environment activated:

```powershell
pytest -q
```

Or without activation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

---

## 4. Environment variables and Sarvam

The app works in deterministic mode by default. Copy `.env.example` to `.env` only if you want to configure Sarvam locally. **Never commit `.env`.**

```env
# Shared
SARVAM_API_KEY=
SARVAM_ENABLED=true

# Phase 2 — Sarvam Document AI Extract
SARVAM_DOCUMENT_LANGUAGE=en-IN
SARVAM_JOB_TIMEOUT_SECONDS=120
SARVAM_POLL_INTERVAL_SECONDS=3

# Phase 1 — optional fictional-content paraphrase
SARVAM_MODEL=gemma4
SARVAM_BASE_URL=https://api.sarvam.ai/v2
SARVAM_TIMEOUT_SECONDS=8
SARVAM_MAX_OUTPUT_TOKENS=180
```

| Variable | Meaning | Default |
|---|---|---|
| `SARVAM_API_KEY` | Optional provider key. Read from `.env`/the environment only. Never logged. Empty or placeholder values disable live calls. | empty |
| `SARVAM_ENABLED` | Explicit opt-in for Sarvam. `false` keeps the deterministic/disabled path. | `false` in a local `.env`; the template suggests `true` after adding a key |
| `SARVAM_DOCUMENT_LANGUAGE` | Document AI language: `en-IN`, `hi-IN` or `bn-IN`. Other values fall back to `en-IN`. | `en-IN` |
| `SARVAM_JOB_TIMEOUT_SECONDS` | Overall Extract job timeout, clamped to 1–600 seconds. | `120` |
| `SARVAM_POLL_INTERVAL_SECONDS` | Extract status poll interval, clamped to 0.1–30 seconds. | `3` |
| `SARVAM_MODEL` | Phase 1 paraphrase model ID. The adapter does not hardwire a model. | `gemma4` |
| `SARVAM_BASE_URL` | OpenAI-compatible base URL for Phase 1 `/v2/chat/completions`. | `https://api.sarvam.ai/v2` |
| `SARVAM_TIMEOUT_SECONDS` | Phase 1 request timeout, clamped to 2–20 seconds. | `8` |
| `SARVAM_MAX_OUTPUT_TOKENS` | Phase 1 output cap, clamped to 40–300. | `180` |

### To leave Sarvam disabled

Do nothing. With no `.env`, or with `SARVAM_ENABLED=false`, the app uses reviewed static English/Hindi fallback explanations and the Phase 2 upload control stays disabled. No network call is made. A placeholder key such as `replace_with_your_sarvam_api_key` is also treated as “not configured”.

### To enable Phase 2 Document AI extraction

1. Copy `.env.example` to `.env`.
2. Put the real key in `SARVAM_API_KEY` (never commit `.env`).
3. Set `SARVAM_ENABLED=true`.
4. Leave `SARVAM_DOCUMENT_LANGUAGE=en-IN` unless the document is Hindi or Bengali.
5. Restart Streamlit, open **Active Insurances → External Insurance**, tick the disclosure acknowledgement, choose a synthetic PDF/PNG/JPG/JPEG, and press **Process document**.

A successful job creates an `OCR_EXTRACTED_NEEDS_REVIEW` record in session state. A failed or rejected job adds nothing and shows an error.

### To enable the optional fictional-content paraphrase

1. Put a key in `.env` (not in code, not in git).
2. Set `SARVAM_ENABLED=true`.
3. Choose a currently documented open-weight model ID in `SARVAM_MODEL`.
4. Restart Streamlit.
5. In Claims Companion, switch on **“Use Sarvam AI for fictional demo content only”**, choose a checklist category, and press **Get AI explanation**.

The adapter rejects the legacy `sarvam-30b` API model ID, validates the response, and falls back to static copy on timeout, exception, empty/overlong output, or adjudicative wording.

### Sarvam privacy boundary (important)

**Phase 1 fictional-content paraphrase (chat-completions):**

- The request can contain only:
  - `language` enum (`en` / `hi`),
  - `claim_type` enum (`health_reimbursement`),
  - `missing_category` enum (one of six fixed categories),
  - `source_excerpt_id` enum (`demo_policy_clause_01` / `demo_checklist_01`),
  - the fixed synthetic excerpt supplied in `src/sarvam_service.py`.
- The public adapter method accepts **no free-text, document, row, message or identifier parameter**. Tests inspect the signature and payload.
- User-entered draft text, uploaded document text, transaction rows, extracted PDF text and case notes are **never** sent to this paraphrase adapter.
- When a user-supplied file is present, the Phase 1 AI control is disabled and says AI is disabled for user-supplied records.
- The model may only paraphrase content the app already displays. It never creates a requirement, deadline, eligibility decision, legal conclusion or payout prediction. The original checklist remains visible.

**Phase 2 Document AI Extract:**

- The **selected document bytes are deliberately transmitted to Sarvam AI** only after the exact disclosure is shown, the acknowledgement checkbox is ticked and **Process document** is pressed. This is the one live external document path in the app.
- Only the document, the fixed extraction JSON schema, the selected `en-IN` / `hi-IN` / `bn-IN` language and `output_format=json` are sent. No Paytm, bank, insurer or government API is contacted.
- The upload is held in memory and is not written to disk, cached, logged or added to the repository. Extracted values are kept in Streamlit session state for review only.
- Logs contain only a generic status, error type and elapsed milliseconds. No document bytes, extracted field values, policy numbers, names or API keys are logged.
- OCR output is fallible and is never treated as insurer verification, proof of active cover or a claims decision.

**Licensing note:** an open-weight model served by Sarvam is not the same as running the weights locally, and it does not make the whole application open source. The app code is MIT-licensed; model/API use remains subject to the provider’s terms and attribution requirements.

---

## 5. Data-flow and privacy model

- **No persistence.** Claim data, checklist markings, tracker entries, drafts, case notes, seeded/external insurance records and nominee links live only in Streamlit session state. There is no database, cloud storage or external analytics.
- **No file writes for uploads.** CSV is parsed from bytes with pandas in memory; PDF/TXT is read from bytes with pypdf in memory; Phase 2 policy files stay in memory for the Sarvam request. Original files are not saved. Extracted text is not persisted outside the session.
- **No content logging.** The app does not log document content, transaction rows, health fields, bank details, policy numbers, names, API keys, raw prompts or raw responses.
- **No analytics/trackers.** `.streamlit/config.toml` disables Streamlit usage statistics. There is no telemetry, tracking pixel or third-party analytics.
- **Uploads.** Phase 1: PDF, TXT and CSV only; 10 MB per file; explicit acknowledgement before file selection; local processing only. Phase 2: PDF, PNG, JPG or JPEG only; 10 MB; 20 PDF pages; explicit disclosure and acknowledgement before the Sarvam call. ZIP and TIFF are rejected.
- **Reset demo.** Clears every app-owned `vs_` session key, including checklist, tracker, draft, Sarvam results, upload acknowledgements, family notes, external policy records and nominee changes. **Reset insurance demo** restores the seeded Phase 2 fixtures.
- **No live integrations.** The app does not query, scrape, automate or submit anything to Paytm, banks, insurers, UPI mandates, Bima Bharosa, IRDAI, RBI, SEBI, IEPFA or any government portal. Official sources are rendered as links for the user to open. Paytm is demo data only.
- **Sarvam.** Optional. Phase 1 is synthetic-only and enum/source-ID-only. Phase 2 sends the selected document to Sarvam Document AI only after explicit acknowledgement; without a configured key, no document call is made. The default demo works with no key and no internet.
- **Local only.** The upload paths must not be deployed to a public URL that accepts real health/financial documents.

---

## 6. Safety and claims guardrails

- The app does not decide coverage, eligibility, claim approval, payout or settlement.
- It does not say a document is valid, authentic, sufficient, accepted or guaranteed to lead to settlement.
- It does not calculate a guaranteed payout or predict the likelihood of approval.
- It does not encode a universal document checklist or a legal/regulatory deadline. Reminder dates are entered by the user from what the insurer stated.
- It does not advise stopping an EMI or insurance premium, and it does not automate cancellation of mandates or policies.
- It never asks for or processes OTPs, passwords, UPI PINs, card PINs or payments to release a claim.
- It does not submit claims, complaints or cancellations.
- Family Finance Finder treats every match as a **lead**, never proof of an asset, loan, policy, balance, beneficiary or ownership. It does not read or repurpose UPI AutoPay mandate details and has no mandate API.
- The app does not ask a relative to authenticate as a deceased person, use that person’s OTP, or access that person’s account. Family/authority verification is out of scope. A death certificate alone is **not** represented as sufficient authority for every record or asset.
- Anti-fraud warning is always available: never pay a fee to receive claim proceeds; never scan a QR code from a stranger; never share an OTP, UPI PIN, password or card PIN. IRDAI/Bima Bharosa does not ask complainants for payment to resolve a grievance.
- IRDAI/Bima Bharosa/Ombudsman eligibility, documents and time limits can vary. The app links the official sources and does not invent a universal rule.
- **Active Insurances** does not read real Paytm accounts, call Paytm, authenticate anyone, make a payment or create a real nomination. All Paytm-style identities, policies, directory matches and acknowledgements are **DEMO/SIMULATED**.
- Seeded policies are labelled **Demo record — not verified with insurer**. OCR output is labelled **OCR extracted — needs review**; reviewed records are labelled **User reviewed — insurer status not verified**.
- An external document is not added as a policy merely because OCR ran. Clearly non-insurance documents are rejected; uncertain or incomplete insurance results go to Needs review.
- Nominee summary sharing is a separate opt-in and is **off by default**. Acceptance alone shows nothing unless the owner allowed sharing. The shared view is a limited summary only and explicitly says **“Insurer nomination not verified”**.
- A death certificate, a demo nominee link or a family relationship is **not** treated as proof of legal authority, beneficial ownership or insurer nomination.

---

## 7. Official sources embedded in the app

These are **navigation links only**. The app does not query, scrape or automate them. The link inventory date is **2026-10-29** (URLs taken from the supplied build specification; page content was not scraped or re-verified during this build). Re-check current wording before relying on any source.

| Source | URL | Purpose |
|---|---|---|
| IRDAI — Health Insurance Department | https://irdai.gov.in/health-dept | Regulator context for health insurance |
| Bima Bharosa — FAQ and grievance route | https://bimabharosa.irdai.gov.in/Home/FAQ | Official grievance FAQ |
| Bima Bharosa portal | https://bimabharosa.irdai.gov.in/ | Official grievance portal link |
| IRDAI — List of insurer Grievance Redressal Officers | https://irdai.gov.in/list-of-gros | Find the insurer GRO route |
| Council for Insurance Ombudsmen | https://www.cioins.co.in/Ombudsman | Ombudsman information |
| Common Landing Portal for Unclaimed Financial Assets | https://www.unclaimedassetsportal.in/ | Starting point for unclaimed assets |
| RBI UDGAM — Unclaimed Deposits | https://udgam.rbi.org.in/unclaimed-deposits/#/login | RBI unclaimed-deposit search |
| IEPFA | https://iepf.gov.in/ | Unclaimed dividends/shares information |
| SEBI Investor Website | https://investor.sebi.gov.in/ | Investor education/grievance navigation |
| Sarvam open-weight API docs | https://docs.sarvam.ai/api/getting-started/models/openweight | Optional provider documentation |
| Sarvam model status | https://docs.sarvam.ai/api/getting-started/models | Current model list/status |
| DPDP Rules backgrounder | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190655&lang=2&reg=48 | Public policy background, not legal advice |

The app says **“We have not searched this portal; open it to verify the lead.”** It does not claim that a portal was queried or that any record exists.

---

## 8. Project structure

```text
Viraasat_Saathi/
├── app.py                       # Streamlit UI and session-only state
├── README.md
├── LICENSE                      # MIT
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml              # theme + usage-stats off
├── data/
│   ├── demo_policy.json         # fictional clause-cited policy
│   ├── demo_claim.json          # fictional checklist + timeline
│   ├── demo_transactions.csv    # synthetic statement
│   ├── source_registry.json     # official link registry
│   ├── mock_paytm_users.json    # seeded demo identities (Phase 2)
│   ├── mock_paytm_policies.json # seeded fictional policies (Phase 2)
│   └── mock_nominee_links.json  # seeded simulated nominee link
├── src/
│   ├── __init__.py
│   ├── models.py                # pydantic fixture/lead/source models
│   ├── fixtures.py              # local fixture loaders (cached in memory)
│   ├── claims_engine.py         # deterministic counts, citations, summary
│   ├── transaction_matcher.py   # explicit keywords + distinct-month rules
│   ├── document_parser.py       # in-memory CSV/PDF/TXT validation
│   ├── draft_templates.py       # deterministic bilingual drafts
│   ├── sarvam_service.py        # optional enum-only Phase 1 paraphrase adapter
│   ├── safety.py                # reset, safety constants, redaction helpers
│   ├── translations.py          # reviewed English/Hindi static strings
│   ├── mock_paytm_data.py       # validated seeded Phase 2 fixtures; no network
│   ├── insurance_inventory.py   # common policy shape, sharing, reset
│   ├── nominee_demo.py          # simulated owner-confirmed nominee links
│   ├── upload_validation.py     # 10 MB, 20-page, MIME/magic checks
│   ├── sarvam_document_ai.py    # real Sarvam Extract async adapter
│   ├── policy_extraction_schema.py # fixed JSON extraction schema
│   ├── policy_normalizer.py     # conservative OCR -> review record
│   └── insurance_ui.py          # Active Insurances dashboard
└── tests/
    ├── conftest.py
    ├── test_claims_engine.py
    ├── test_transaction_matcher.py
    ├── test_safety.py
    ├── test_sarvam_service.py
    ├── test_app_smoke.py
    └── test_phase2_insurance.py
```

---

## 9. Automated tests

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers:

- exact required-document count after checklist toggles,
- neutral status wording and `insurer_validated=False`,
- every verified policy answer carries a clause ID and page,
- unknown policy topics return “Not verified”,
- demo statement produces four lead categories,
- every lead includes exact source rows,
- a single transaction is low-confidence and not recurring,
- multiple same-month rows do **not** satisfy monthly recurrence,
- distinct months do satisfy recurrence,
- punctuation/case normalisation and token-aware keyword matching,
- malformed CSV rejection,
- 10 MB upload limit and unsupported file types,
- in-memory PDF parsing with a no-disk-write guard and OCR-not-supported message,
- reset clears all app session keys,
- English/Hindi translation key parity and safety-copy checks,
- source registry uses HTTPS and contains the required official sources,
- Sarvam adapter signature accepts only enums/source IDs, never free text,
- Sarvam disabled mode, missing key, deprecated model, success, timeout fallback, malformed/adjudicative output fallback, and no payload logging,
- Phase 2 demo user switching and seeded policy filtering,
- no Paytm network imports, URLs or fixtures containing phone/email identifiers,
- Phase 2 upload type, magic-byte, 10 MB and 20-page limits; ZIP/TIFF rejection,
- missing/placeholder key and disabled-mode behaviour with no client call,
- Sarvam Extract lifecycle: submit, poll, results, object/dict responses, partial completion, timeout, failed/rejected and SDK errors,
- conservative OCR normalisation, non-insurance rejection, missing values, masking and the review gate to `USER_REVIEWED_UNVERIFIED`,
- nominee owner confirmation, separate summary sharing defaulting off, accept/decline/revoke and limited-summary visibility,
- Streamlit smoke tests for home and all three journeys, checklist count, draft review gate, tracker, insurance sections/user switch, reset and language switching.

---

## 10. Three-minute demo guide

### 0:00–0:20 — Concept

> “Virasat Saathi offers financial guidance when you need it and support when it matters most. It has a claims journey for current policyholders and a family-support journey after a loss. It explains and assists; deterministic rules check; official sources establish requirements; the user decides.”

### 0:20–1:35 — Claims Companion

1. Click **Claims Companion**.
2. Click **Load demo claim** (`DEMO-CLAIM-001`).
3. Show the fictional policy lookup and a clause citation such as `demo_policy_clause_01 · page 3`.
4. Tick **Completed claim form** and **Policy schedule**; leave **Itemised final hospital bill** unmarked.
5. Point out the deterministic remaining count and the note that this is **not insurer validation**.
6. In **Help me respond**, generate the missing-document follow-up. Show that the draft is editable, tick the review checkbox, and download it. Emphasise: **nothing is sent**.
7. In **Track next steps**, enter a reminder date stated by the insurer (or leave blank) and tick **Mark done** for one step.
8. Show the anti-fraud warning and official escalation links.

### 1:35–2:15 — Family Finance Finder

1. Go back home and open **Family Finance Finder**.
2. Click **Load synthetic statement**.
3. Show the four possible leads: insurance payment, SIP-like debit, lender EMI, recurring subscription.
4. Open one lead and show the exact transaction rows, the keyword/rule explanation, pattern strength, “what this does not prove” and suggested next step.
5. Open an official link card and read: **“We have not searched this portal; open it to verify the lead.”**

### 2:15–3:05 — Active Insurances (Phase 2)

1. **Start at the sign-in screen.** Show the two preset accounts (Aarav Sharma / aarav123, Meera Sharma / meera123). Sign in as **Aarav Sharma**. The top-right header now shows the signed-in profile with **Log out**.
2. Open **Active Insurances**. Show the persistent **“Independent hackathon prototype · Paytm-style experience · No live Paytm connection”** strip and Aarav Sharma’s three seeded policies. The inventory is scoped to the signed-in account.
3. Click the **Policy document** tab on any policy card. Show the generated PDF preview with masked policy number and the **Download policy document** button. Explain that seeded policies generate PDFs on the fly; uploaded external policies show the original file bytes.
4. **Switch accounts via logout/login:** click **Log out** (top right), then sign in as **Meera Sharma**. Open **Active Insurances** — Meera sees only her Travel policy. Log out and back in as Aarav to continue.
5. Open **External Insurance**. Point out the exact disclosure, the unchecked acknowledgement and the disabled upload/process controls. If a real key is configured, upload a **synthetic** PDF/PNG/JPG/JPEG, tick the box, press **Process document**, then show the `OCR_EXTRACTED_NEEDS_REVIEW` record and its review form. If no key is configured, show **“Add SARVAM_API_KEY to .env to enable document extraction.”** and explain that no fake OCR is returned.
6. Open **Nominee-linked Policies** as Meera Sharma. Show the seeded accepted family-sharing link and the limited summary (masked policy number, no premium or full number). Read **“Insurer nomination not verified.”** Then switch to Aarav Sharma (logout/login), open **Manage nominee** on the health policy, show that the owner confirmation is unticked and summary sharing is off by default, create a sharing link, switch back to Meera, and accept or decline it.

### 3:05–3:25 — Trust and AI

1. Show the **Sources & limitations** expander and the privacy banner.
2. If Sarvam is configured, switch on the fictional-content AI toggle and request one checklist explanation. Otherwise show the deterministic English/Hindi fallback.
3. Close with: **“The model explains; the rules check; the institution decides.”**

---

## 11. Known limitations and out of scope

- No live banking, insurer, UPI-mandate, government-portal or Account Aggregator integration.
- No real Paytm transaction-history access, Paytm API/SDK, credentials or authentication; all Paytm-style data and family-sharing links are local to the prototype.
- The prototype includes a local **sign-in screen with preset credentials** for demonstration; this is not a real authentication system. No Aadhaar, OTP or account access.
- No claim submission, settlement, money transfer, account closure, loan repayment or mandate cancellation.
- No email/SMS/WhatsApp notification integration.
- No universal claims checklist and no legal/regulatory deadline calculation.
- No coverage, eligibility, approval, payout or likelihood prediction.
- No handwriting extraction, medical interpretation or document authenticity verification.
- **Sarvam Document AI output is OCR, not insurer verification.** It can miss, misread or misclassify fields. Missing values remain **Not found in document**; users must review before relying on a record.
- The external policy inventory is session-only; there is no insurer feed, policy verification, renewal check or active-cover confirmation.
- Nominee linking is a **family-sharing link inside the prototype**, not an insurer nomination, legal heir determination or authority verification. A death certificate alone is not presented as sufficient authority for every record or asset.
- No arbitrary real-policy Q&A; the policy answers come from the fictional fixture only.
- No public cloud deployment that accepts real health/financial documents.
- No voice/audio mode.
- Official link page content is not scraped, re-verified or guaranteed current. Requirements can vary by insurer and product.
- Sarvam is optional; its availability, model IDs, API shape and output quality can change. The app never depends on it for the main journey.
- The app is a prototype, not a production security-reviewed service. Real deployment would require partner approval, security review, a privacy notice, contracts and legal/regulatory review.

---

## 12. Licensing and attribution

- **Application code:** MIT License. See `LICENSE`.
- **Synthetic fixtures:** created for this prototype; fictional and not a real insurance product, claim, statement or financial record.
- **Dependencies (licences as published by their projects):**
  - Streamlit — Apache License 2.0
  - pandas — BSD 3-Clause
  - pydantic — MIT
  - python-dotenv — BSD 3-Clause
  - pypdf — BSD 3-Clause
  - OpenAI Python SDK — Apache License 2.0
  - sarvamai — provider SDK licence as published by Sarvam AI
  - pytest — MIT
- **Optional Sarvam AI:** provider/API attribution and terms apply. Phase 1 uses an open-weight model served by Sarvam through an OpenAI-compatible API; it does **not** run the model weights locally and does **not** make the whole application open source. The adapter is configurable and defaults to `gemma4`; check the current Sarvam model-status documentation before enabling it. Phase 2 calls the Sarvam Document AI Extract API through the `sarvamai` SDK; its data-handling and retention terms apply to uploaded documents.
- **No third-party logos or Paytm branding** are used. The abstract mark is a simple local SVG.
- **No affiliation:** Paytm, any insurer, IRDAI, RBI, SEBI, IEPFA, the Council for Insurance Ombudsmen and Sarvam AI are not affiliated with this prototype.

---

## 13. Troubleshooting

- **`streamlit` not found:** activate the virtual environment or use `.\.venv\Scripts\python.exe -m streamlit run app.py`.
- **PowerShell activation blocked:** use the direct `.\.venv\Scripts\python.exe` commands above.
- **Port 8501 in use:** `streamlit run app.py --server.port 8502`.
- **Sarvam toggle disabled:** this is expected without `SARVAM_ENABLED=true` and a key. The deterministic demo is fully functional.
- **Phase 2 upload controls disabled:** add a real `SARVAM_API_KEY` to `.env`, set `SARVAM_ENABLED=true`, restart Streamlit, and tick the disclosure acknowledgement. A placeholder key is treated as not configured.
- **Sarvam Phase 1 request fails:** the app falls back automatically; the claim checklist and drafts are never blocked.
- **Sarvam Document AI request fails:** the app shows an error, adds no policy record, and keeps the seeded policies available. Check the key, network, file type, 10 MB/20-page limits and job status message.
- **PDF shows “OCR is not supported”:** that is the Phase 1 claims readability check. Phase 2 uses Sarvam Document AI for permitted policy files.
- **Upload rejected:** Phase 1 accepts PDF/TXT (claims) and CSV (Family Finder); Phase 2 accepts PDF/PNG/JPG/JPEG, maximum 10 MB and 20 PDF pages. ZIP and TIFF are rejected.

---

## 14. P0 acceptance mapping

| Requirement | Where it is implemented |
|---|---|
| Fresh setup works | README exact commands; `requirements.txt`; tested on Python 3.14.6 |
| App starts without Sarvam/internet | `SARVAM_ENABLED=false`; deterministic fallbacks; no required network |
| Home shows all three journeys + demo/privacy notice | `app.py` home cards + persistent banner |
| Claims loads fictional policy/claim with citations | `data/demo_policy.json`, `data/demo_claim.json`, `src/claims_engine.py` |
| Checklist toggles change remaining count correctly | `checklist_progress` + Streamlit checkbox state |
| Draft generated/copied/downloaded without submission | `src/draft_templates.py`; review gate; `.txt` download |
| Tracker updates in session; Reset clears | `vs_step_*` session keys; `reset_session_state` |
| Family Finder identifies categories with evidence | `src/transaction_matcher.py`; exact `EvidenceRow` list |
| Single rows not labelled recurring | `is_recurring` requires ≥2 distinct months |
| Every lead says it is a lead and needs confirmation | lead note + category caveats |
| Official-link cards open configured domains; no search claim | `source_registry.json`; link buttons; “not searched” captions |
| Deterministic English/Hindi explanations with Sarvam off | `src/translations.py`; `deterministic_explanation` |
| Sarvam adapter accepts only synthetic enum/source fields | `SarvamService.explain_demo_checklist` signature + tests |
| Sarvam exceptions fall back gracefully | `_fallback`; timeout/malformed tests |
| No content/API key/health/bank/prompt logs or disk writes | no content logging; in-memory parsers; no-disk-write test |
| Uploads local/in-memory; no Sarvam; OCR message | `src/document_parser.py`; upload acknowledgement |
| No live Paytm/bank/insurer/government integrations or automatic submissions | mock-only Paytm code; links only; no submission buttons |
| Phase 2 Sarvam is the only live external call | `src/sarvam_document_ai.py`; disabled without key |
| Fraud warning covers fee/QR/OTP/PIN/password | `anti_fraud_warning` in both languages |
| Active Insurances dashboard has all three sections | `src/insurance_ui.py`; section radio keys |
| Seeded Paytm users/policies are simulated and filter by user | `data/mock_paytm_*.json`; `src/mock_paytm_data.py`; `paytm_policies_for_user` |
| No Paytm API/network/credentials; no real auth | source guard test; mock-only fixtures |
| Upload limits and consent gate | `src/upload_validation.py`; unchecked acknowledgement; explicit Process button |
| Real Sarvam Extract lifecycle with no fake success | `src/sarvam_document_ai.py`; mocked lifecycle tests; disabled/error paths |
| OCR creates Needs review; missing fields stay missing | `src/policy_normalizer.py`; `OCR_EXTRACTED_NEEDS_REVIEW`; review form |
| Non-insurance docs rejected; uncertain docs go to review | `classify_document`; `build_external_policy` |
| Owner confirmation + separate summary sharing off by default | `src/nominee_demo.py`; nominee checkboxes |
| Accept/decline/revoke and limited nominee view | `respond_to_nominee_link`; `revoke_nominee_link`; `limited_shared_summary` |
| Reset restores Phase 2 fixtures | `reset_insurance_session`; global `reset_session_state` |

---

**Prototype status:** working local demo, deterministic by default, synthetic-data-only. Real-data processing is not approved for this build.
