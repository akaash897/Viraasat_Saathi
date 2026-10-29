# Virasat Saathi

**Financial guidance when you need it. Support when it matters most.**

Virasat Saathi is an independent, local-first hackathon prototype with two financial-guidance journeys:

1. **Claims Companion** — helps a living policyholder understand a *fictional* sample health-insurance policy, prepare a reimbursement checklist, see which document categories are still unmarked, draft a follow-up, and track next steps.
2. **Family Finance Finder** — reads a *synthetic* transaction statement, finds possible insurance / investment / loan / recurring-payment clues, shows the exact rows behind each lead, and routes the user to official channels for verification.

Both journeys share an evidence-first case panel, clear source labels and a session-only tracker. The product rule is:

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

### Shared

- English / Hindi UI toggle with reviewed static strings for key labels, instructions, status wording, fallbacks and all safety-critical disclaimers.
- Calm off-white / navy / teal / restrained saffron visual theme.
- Persistent “Independent hackathon prototype · Demo data” label.
- **Reset demo** clears all session data and returns to the synthetic case.
- **Sources & limitations** expander listing every official link and what the prototype cannot verify.
- Optional Sarvam AI paraphrase for fictional checklist content only. The app works fully with no API key and no internet access.

---

## 3. Requirements and exact setup

### Runtime

- Python **3.11+** (tested here with Python **3.14.6** on Windows).
- `pip`.
- No database, cloud account or internet connection is required for the default demo.
- Optional internet only if you deliberately enable Sarvam.

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
SARVAM_API_KEY=
SARVAM_MODEL=gemma4
SARVAM_BASE_URL=https://api.sarvam.ai/v2
SARVAM_ENABLED=false
SARVAM_TIMEOUT_SECONDS=8
SARVAM_MAX_OUTPUT_TOKENS=180
```

| Variable | Meaning | Default |
|---|---|---|
| `SARVAM_API_KEY` | Optional provider key. Read from the environment only. Never logged. | empty |
| `SARVAM_MODEL` | Configurable open-weight model ID. The adapter does not hardwire a model. | `gemma4` |
| `SARVAM_BASE_URL` | OpenAI-compatible base URL for current `/v2/chat/completions`. | `https://api.sarvam.ai/v2` |
| `SARVAM_ENABLED` | Explicit opt-in. `false` keeps the deterministic path. | `false` |
| `SARVAM_TIMEOUT_SECONDS` | Conservative request timeout, clamped to 2–20 seconds. | `8` |
| `SARVAM_MAX_OUTPUT_TOKENS` | Conservative output cap, clamped to 40–300. | `180` |

### To leave Sarvam disabled

Do nothing. With no `.env`, or with `SARVAM_ENABLED=false`, the app uses reviewed static English/Hindi fallback explanations. No network call is made. The UI shows the deterministic explanation and a status label.

### To enable the optional fictional-content paraphrase

1. Put a key in `.env` (not in code, not in git).
2. Set `SARVAM_ENABLED=true`.
3. Choose a currently documented open-weight model ID in `SARVAM_MODEL`.
4. Restart Streamlit.
5. In Claims Companion, switch on **“Use Sarvam AI for fictional demo content only”**, choose a checklist category, and press **Get AI explanation**.

The adapter rejects the legacy `sarvam-30b` API model ID, validates the response, and falls back to static copy on timeout, exception, empty/overlong output, or adjudicative wording.

### Sarvam privacy boundary (important)

- The request can contain only:
  - `language` enum (`en` / `hi`),
  - `claim_type` enum (`health_reimbursement`),
  - `missing_category` enum (one of six fixed categories),
  - `source_excerpt_id` enum (`demo_policy_clause_01` / `demo_checklist_01`),
  - the fixed synthetic excerpt supplied in `src/sarvam_service.py`.
- The public adapter method accepts **no free-text, document, row, message or identifier parameter**. Tests inspect the signature and payload.
- User-entered draft text, uploaded document text, transaction rows, extracted PDF text and case notes are **never** sent to Sarvam.
- When a user-supplied file is present, the UI disables AI and says AI is disabled for user-supplied records.
- Logs contain only a generic `status=success|fallback` and elapsed milliseconds. No prompt, response, key, file content or transaction row is logged.
- The model may only paraphrase content the app already displays. It never creates a requirement, deadline, eligibility decision, legal conclusion or payout prediction. The original checklist remains visible.

**Licensing note:** an open-weight model served by Sarvam is not the same as running the weights locally, and it does not make the whole application open source. The app code is MIT-licensed; model/API use remains subject to the provider’s terms and attribution requirements.

---

## 5. Data-flow and privacy model

- **No persistence.** Claim data, checklist markings, tracker entries, drafts, case notes and uploads live only in Streamlit session state. There is no database, cloud storage or external analytics.
- **No file writes for uploads.** CSV is parsed from bytes with pandas in memory; PDF/TXT is read from bytes with pypdf in memory. Original files are not saved. Extracted text is not persisted.
- **No content logging.** The app does not log document content, transaction rows, health fields, bank details, API keys, raw prompts or raw responses.
- **No analytics/trackers.** `.streamlit/config.toml` disables Streamlit usage statistics. There is no telemetry, tracking pixel or third-party analytics.
- **Uploads.** PDF, TXT and CSV only; 10 MB per file; explicit acknowledgement before file selection; local processing only. Scanned PDFs get an “OCR is not supported” message.
- **Reset demo.** Clears every app-owned `vs_` session key, including checklist, tracker, draft, Sarvam result, upload acknowledgement and family notes.
- **No live integrations.** The app does not query, scrape, automate or submit anything to Paytm, banks, insurers, UPI mandates, Bima Bharosa, IRDAI, RBI, SEBI, IEPFA or any government portal. Official sources are rendered as links for the user to open.
- **Sarvam.** Optional, synthetic-only, enum/source-ID-only. The default demo works with no key and no internet.
- **Local only.** The upload path must not be deployed to a public URL that accepts real health/financial documents.

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
│   └── source_registry.json     # official link registry
├── src/
│   ├── __init__.py
│   ├── models.py                # pydantic fixture/lead/source models
│   ├── fixtures.py              # local fixture loaders (cached in memory)
│   ├── claims_engine.py         # deterministic counts, citations, summary
│   ├── transaction_matcher.py   # explicit keywords + distinct-month rules
│   ├── document_parser.py       # in-memory CSV/PDF/TXT validation
│   ├── draft_templates.py       # deterministic bilingual drafts
│   ├── sarvam_service.py        # optional enum-only Sarvam adapter
│   ├── safety.py                # reset, safety constants, redaction helpers
│   └── translations.py          # reviewed English/Hindi static strings
└── tests/
    ├── conftest.py
    ├── test_claims_engine.py
    ├── test_transaction_matcher.py
    ├── test_safety.py
    ├── test_sarvam_service.py
    └── test_app_smoke.py
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
- Streamlit smoke tests for home, both journeys, checklist count, draft review gate, tracker, reset and language switching.

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

### 1:35–2:25 — Family Finance Finder

1. Go back home and open **Family Finance Finder**.
2. Click **Load synthetic statement**.
3. Show the four possible leads: insurance payment, SIP-like debit, lender EMI, recurring subscription.
4. Open one lead and show the exact transaction rows, the keyword/rule explanation, pattern strength, “what this does not prove” and suggested next step.
5. Open an official link card and read: **“We have not searched this portal; open it to verify the lead.”**

### 2:25–3:00 — Trust and AI

1. Show the **Sources & limitations** expander and the privacy banner.
2. If Sarvam is configured, switch on the fictional-content AI toggle and request one checklist explanation. Otherwise show the deterministic English/Hindi fallback.
3. Close with: **“The model explains; the rules check; the institution decides.”**

---

## 11. Known limitations and out of scope

- No live banking, insurer, UPI-mandate, government-portal or Account Aggregator integration.
- No real Paytm transaction-history access and no claim that Paytm APIs are available.
- No login, authentication, Aadhaar, OTP or account access.
- No claim submission, settlement, money transfer, account closure, loan repayment or mandate cancellation.
- No email/SMS/WhatsApp notification integration.
- No universal claims checklist and no legal/regulatory deadline calculation.
- No coverage, eligibility, approval, payout or likelihood prediction.
- No OCR, handwriting extraction, medical interpretation or document authenticity verification.
- No arbitrary real-policy Q&A; the policy answers come from the fictional fixture only.
- No legal-heir determination or authority verification. A death certificate alone is not presented as sufficient authority for every record or asset.
- No public cloud deployment that accepts real health/financial documents.
- No voice/audio mode.
- Official link page content is not scraped, re-verified or guaranteed current. Requirements can vary by insurer and product.
- Sarvam is optional; its availability, model IDs and output quality can change. The app never depends on it for the main journey.
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
  - pytest — MIT
- **Optional Sarvam AI:** provider/API attribution and terms apply. The prototype uses an open-weight model served by Sarvam through an OpenAI-compatible API; it does **not** run the model weights locally and does **not** make the whole application open source. The adapter is configurable and defaults to `gemma4`; check the current Sarvam model-status documentation before enabling it.
- **No third-party logos or Paytm branding** are used. The abstract mark is a simple local SVG.
- **No affiliation:** Paytm, any insurer, IRDAI, RBI, SEBI, IEPFA, the Council for Insurance Ombudsmen and Sarvam AI are not affiliated with this prototype.

---

## 13. Troubleshooting

- **`streamlit` not found:** activate the virtual environment or use `.\.venv\Scripts\python.exe -m streamlit run app.py`.
- **PowerShell activation blocked:** use the direct `.\.venv\Scripts\python.exe` commands above.
- **Port 8501 in use:** `streamlit run app.py --server.port 8502`.
- **Sarvam toggle disabled:** this is expected without `SARVAM_ENABLED=true` and a key. The deterministic demo is fully functional.
- **Sarvam request fails:** the app falls back automatically; the claim checklist and drafts are never blocked.
- **PDF shows “OCR is not supported”:** the file is scanned/image-only. OCR is intentionally out of scope.
- **Upload rejected:** only PDF/TXT in the claims readability check, CSV in Family Finder, and each file must be at most 10 MB.

---

## 14. P0 acceptance mapping

| Requirement | Where it is implemented |
|---|---|
| Fresh setup works | README exact commands; `requirements.txt`; tested on Python 3.14.6 |
| App starts without Sarvam/internet | `SARVAM_ENABLED=false`; deterministic fallbacks; no required network |
| Home shows both journeys + demo/privacy notice | `app.py` home cards + persistent banner |
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
| No live integrations or automatic submissions | no integration code; no submission buttons |
| Fraud warning covers fee/QR/OTP/PIN/password | `anti_fraud_warning` in both languages |

---

**Prototype status:** working local demo, deterministic by default, synthetic-data-only. Real-data processing is not approved for this build.
