irasat Saathi — Nominee Intelligence & Family Claim Orchestrator
OpenCode incremental implementation plan
Scope: Two focused capabilities that extend the existing Phase 1–4 application:
1. Cross-Policy Nominee Consistency Intelligence — inspect nominee information across a user's policy portfolio and compare it with consented, simulated Paytm-linked family profile data.
2. AI Family Claim Orchestrator — turn one family/death event into separate, policy-specific claim-preparation workflows, coordinated through one family case.
Important integration boundary: All Paytm identity, profile lookup, linked-account, policy-purchase and insurer-response behaviour remains mock-only. Sarvam Document AI and Sarvam-105B are real integrations when the existing Sarvam key is configured. Do not add Paytm API calls or request Paytm credentials.
0. Instructions to OpenCode — read first
1. Inspect the existing repository and read the existing Phase 1, Phase 2 and Phase 3/4 specifications before making changes.
2. Extend the current application. Do not rebuild it, replace its framework, or remove existing functionality.
3. Reuse the existing policy inventory, Sarvam Document AI adapter, mock Paytm user directory, nominee-linking flow, FamilyCase model, Claims Saathi, claim documents and tracker wherever possible.
4. Keep Paytm entirely simulated. Every simulated profile, linked Paytm ID, insurer acknowledgement, policy status and family-access approval must be visibly labelled DEMO or SIMULATED.
5. Use real Sarvam API calls only when SARVAM_API_KEY is configured. Never fabricate a successful OCR or LLM response. Provide clear errors and a deterministic non-AI fallback for non-sensitive workflow operations.
6. Use synthetic fixtures only for this hackathon. Do not upload actual death certificates, identity proofs, policy documents, nominee details or health/financial records.
7. The LLM must never decide legal eligibility, authenticate identity, approve family access, validate a government certificate, or settle/approve a claim. Backend rules and an explicit simulated human-review action control state changes.
8. Make the smallest additive changes possible. Keep current routes, visual system, persistence approach and tests.
9. Before completion, run existing and new tests, fix regressions, and provide exact run instructions plus a short demo script.
Definition of a working prototype
- A logged-in demo user can analyse all policies in their portfolio together.
- Linked demo Paytm profiles can be retrieved from the local mock directory only after the simulated family link and profile-sharing consent are accepted.
- The app detects explainable nominee data discrepancies and age/guardian review flags, with evidence for every finding.
- A permitted family case can generate a single parent case and separate child workflows for policies relevant to the death event.
- Sarvam-105B explains the deterministic findings and helps the user understand the next steps, but cannot create an unverified fact or bypass backend controls.
- Every policy workflow has its own event relevance, checklist, missing documents, draft and user-managed status.
Part A — Cross-Policy Nominee Consistency Intelligence
1. User journey
Add an entry point inside Active Insurances:

Active Insurances → Nominee 360 → Analyse my portfolio

Show a short notice before analysis:
“Virasat Saathi will compare nominee details visible in your saved policy records with information shared by family members through the simulated Paytm link. This is a data-consistency check, not proof of identity, legal eligibility or insurer registration. You can review every finding before taking action.”

The user can run the analysis after choosing which linked family profiles may be included. Only show the minimum profile fields needed for comparison.
Analysis flow
1. Load policies belonging to the currently logged-in demo user.
2. Read nominee details and provenance from each policy record.
3. Load only family profiles linked to that user where the invitation is accepted and the nominee has consented to share the required demo profile fields.
4. Normalise and compare nominee names, date of birth (DOB), stated relationship and guardian/appointee information where present.
5. Apply deterministic validation rules to produce findings.
6. Send a redacted summary of the findings to Sarvam-105B for plain-language explanations and grouped observations.
7. Validate the LLM's response against a strict schema. The backend remains authoritative for severity, findings and statuses.
8. Display a portfolio report with policy-level evidence, suggested user checks and clear limitations.
9. Let the user mark a finding as reviewed, corrected in the demo record, or “intentionally different”. Never auto-change any policy nominee.
2. Mock Paytm linked-profile lookup
Create or reuse a local mock identity directory. Do not call Paytm APIs.

Each simulated profile may expose only these fields to this feature:
{
  "demo_paytm_user_id": "paytm.demo.meera",
  "display_name": "Meera Sharma",
  "legal_name_demo": "Meera R Sharma",
  "date_of_birth": "1991-04-12",
  "age_band": "ADULT",
  "relationship_to_policyholder": "SPOUSE",
  "profile_verified_demo": true,
  "family_link_status": "ACCEPTED",
  "profile_sharing_consent": true,
  "consented_fields": ["legal_name_demo", "date_of_birth", "relationship_to_policyholder"]
}
Requirements:
- Use fictional identifiers and fictional people only. Do not use real phone numbers, email addresses, Aadhaar, PAN, bank details or real Paytm account identifiers.
- A profile lookup is allowed only after the family link is accepted and the linked user has consented to sharing the specific fields.
- The UI must show that this is a simulated Paytm profile lookup.
- If consent is absent or withdrawn, do not expose DOB or legal-name comparison fields. Show Profile details not shared instead.
- Do not infer relationships from names, gender, surnames or the LLM. Relationship must come from an explicit demo profile field or policy document.
- Do not treat profile_verified_demo: true as real KYC verification.
3. Fields to compare
Normalise the existing Phase 2/3 policy record into the following nominee object where information is present:
{
  "nominee_record_id": "nom_demo_001",
  "policy_id": "pol_demo_001",
  "nominee_name_as_printed": "MEERA R SHARMA",
  "nominee_dob_as_printed": "1991-04-12",
  "nominee_relationship_as_printed": "SPOUSE",
  "nominee_share_percent": 100,
  "guardian_or_appointee_name": null,
  "guardian_or_appointee_relationship": null,
  "source_type": "POLICY_SCHEDULE_OCR",
  "source_reference": "doc_demo_001",
  "source_page": 4,
  "source_confidence": 0.93,
  "insurer_registration_status": "OCR_EXTRACTED_UNVERIFIED"
}
Only compare fields actually present in the source. A missing OCR value is NOT_FOUND_IN_DOCUMENT, not proof that the insurer has no such information.

Compare:
- Nominee name on the policy vs consented linked-profile legal/display name.
- DOB on the policy vs consented linked-profile DOB.
- Relationship stated in the policy vs the relationship explicitly declared in the mock family link/profile.
- Age of nominee at the relevant date where DOB is available.
- Guardian/appointee details for a minor where the applicable product/policy rules require review.
- Nominee allocation percentages where the policy record explicitly contains shares.
- Nominee records across different policies, but only to describe differences; do not assume different nominees are a defect.
- Source and insurer-registration status: OCR extracted, user confirmed, mock insurer acknowledgement, or unknown.
4. Deterministic comparison rules
Implement a separate service, for example nominee_consistency_service.py or the equivalent in the existing stack. Do not ask the LLM to calculate ages, compare dates, decide exact mismatches or assign legal eligibility.
4.1 Name comparison
- Unicode-normalise and trim whitespace.
- Case-fold and remove common punctuation/honorifics for comparison only.
- Compare exact normalised values first.
- Use a local fuzzy string matcher (existing dependency if available; otherwise a small deterministic implementation) to identify possible spelling/initial/order variations.
- Display the original strings side-by-side with their source.
- Fuzzy match thresholds are prototype heuristics only. Suggested: exact match; high-similarity candidate; manual-review candidate; no candidate. Store the score and method.
- Never auto-merge records or assert two people are identical solely from name similarity.
- An Indic transliteration or LLM-suggested equivalent may be displayed as a candidate for human review only. Do not use it to grant access or change identity links.
4.2 DOB and age checks
- Parse DOB only if the source value is complete and unambiguous.
- Calculate age using the exact reference date; do not use current age when the workflow relates to a past death event.
- If DOBs differ, create DOB_MISMATCH_REVIEW with both source values.
- If DOB is missing or ambiguous, create DOB_NOT_AVAILABLE; do not estimate age.
- For India-domiciled demo profiles, use 18 as the general age-of-majority threshold for a review flag, based on Section 3 of the Majority Act, 1875. Do not turn this into a blanket insurer-eligibility decision.
4.3 Minor nominee and appointee handling — critical
Do not label a minor nominee as INELIGIBLE by default.

For life insurance, Section 39(1) of the Insurance Act, 1938 expressly contemplates a minor nominee and permits the policyholder to appoint a person, in the insurer's prescribed manner, to receive the money during the nominee's minority. Therefore:
- If a life-policy nominee is under 18 at the relevant death/claim date and no appointee/guardian details are recorded in the available source, flag MINOR_NOMINEE_APPOINTEE_REVIEW.
- If appointee details are present in an OCR source but insurer registration is not confirmed, flag APPOINTEE_DETAILS_UNVERIFIED.
- If the DOB suggests the nominee is an adult at the relevant event date, do not apply the minor flag.
- If the DOB or event date is unavailable, flag AGE_STATUS_UNKNOWN.
- For health/general/other products, do not reuse the life-policy Section 39 rule automatically. Use an insurer/product-specific checklist fixture or return PRODUCT_RULE_CONFIRMATION_REQUIRED.
- Explain that a minor nominee is not automatically invalid and that the insurer must confirm the process and accepted appointee/guardian details.
4.4 Relationship checks
- Compare only two explicit source values.
- If they differ, flag RELATIONSHIP_MISMATCH_REVIEW and display the exact values.
- A difference can be intentional or a data-entry error. Do not auto-correct it.
- Never infer family relationship from a surname, name similarity, gender or LLM guess.
4.5 Allocation checks
- If there are multiple nominees and the source explicitly contains percentages, calculate the total deterministically.
- If the recorded shares do not total 100%, flag NOMINEE_SHARE_TOTAL_REVIEW.
- If no allocation is printed, return SHARE_NOT_FOUND; do not assume equal shares.
- Do not change allocations or recommend that all policies use identical allocations.
4.6 Nomination and registration status
Use explicit provenance statuses:
- INSURER_ACKNOWLEDGED_DEMO — only for a seeded demo insurer acknowledgement.
- POLICY_SCHEDULE_RECORDED — data found in policy schedule; source authenticity is not established by OCR alone.
- OCR_EXTRACTED_UNVERIFIED — nominee details extracted from an uploaded document.
- USER_ENTERED_UNVERIFIED — entered by user, not confirmed by insurer.
- NOT_FOUND_IN_DOCUMENT — OCR did not find the field in the uploaded pages.
- INSURER_STATUS_UNKNOWN — no authoritative status available.
Never turn NOT_FOUND_IN_DOCUMENT into NO_NOMINEE_EXISTS. Only show No nomination recorded in this demo insurer record when the fixture explicitly contains an insurer-status field that says so.
5. Finding categories and severity
The rules engine should return findings in a stable machine-readable schema:
{
  "finding_id": "find_demo_001",
  "policy_id": "pol_demo_001",
  "finding_code": "MINOR_NOMINEE_APPOINTEE_REVIEW",
  "severity": "ATTENTION",
  "status": "OPEN",
  "summary": "Nominee appears to be a minor at the event date",
  "evidence": [
    {"label": "DOB on linked demo profile", "value": "2012-03-04", "source": "MOCK_LINKED_PROFILE"},
    {"label": "Event date", "value": "2026-10-01", "source": "FAMILY_CASE"}
  ],
  "explanation_key": "minor_nominee_life_policy_appointee_review",
  "recommended_user_action": "Check the insurer's appointee requirements for this policy",
  "requires_human_review": true
}
Suggested finding codes:
- NAME_VARIATION_REVIEW
- POSSIBLE_NAME_MISMATCH
- DOB_MISMATCH_REVIEW
- DOB_NOT_AVAILABLE
- RELATIONSHIP_MISMATCH_REVIEW
- MINOR_NOMINEE_APPOINTEE_REVIEW
- APPOINTEE_DETAILS_UNVERIFIED
- AGE_STATUS_UNKNOWN
- NOMINEE_SHARE_TOTAL_REVIEW
- NOMINATION_NOT_FOUND_IN_UPLOADED_DOCUMENT
- INSURER_REGISTRATION_NOT_CONFIRMED
- DIFFERENT_NOMINEES_ACROSS_POLICIES
- PROFILE_DETAILS_NOT_SHARED
- PRODUCT_RULE_CONFIRMATION_REQUIRED
Severity should be assigned by deterministic rules, not the LLM:
- INFO: differences that may be intentional, such as different nominees on different policies.
- ATTENTION: data inconsistency, missing field, minor/appointee review or unconfirmed insurer status.
- REVIEW_REQUIRED: ambiguous identity match, source conflict, unclear DOB, or product rule requiring insurer confirmation.
Do not use INVALID, INELIGIBLE, FRAUD, CLAIM_REJECTED or other conclusive labels.
6. Sarvam-105B role in nominee intelligence
Use the existing Sarvam client and key. Use model ID sarvam-105b through the currently documented Chat Completions API. Keep the provider adapter server-side.

Official docs:
- Chat completions, tool calling and structured output: https://docs.sarvam.ai/api/token-factory/chat-completions
- Sarvam-105B model/API information: https://docs.sarvam.ai/api/getting-started/models/sarvam-105b
- Document AI Extract: https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/how-to/extract
LLM input
Only send the minimum synthetic/redacted comparison data needed to explain findings. Do not send original files, full policy wording, full policy numbers, actual phone numbers, Aadhaar/PAN, bank details, or real personal data.

The LLM may:
- Group similar findings into a readable summary.
- Explain why a name or DOB difference needs human review.
- Explain that different nominees across policies can be intentional.
- Explain the minor/appointee flag in plain English or Hindi using supplied legal/source snippets.
- Suggest what the user should verify with the insurer.
The LLM must not:
- Set or change finding severity.
- Decide whether a person is legally eligible to receive proceeds.
- Decide whether two identities are the same person.
- infer relationships or nominee rights.
- update a policy or nominee record.
- approve a nominee, claim or family access.
Prefer structured output with an explicit schema, e.g.:
{
  "portfolio_summary": "string",
  "finding_explanations": [
    {
      "finding_id": "string",
      "plain_language_explanation": "string",
      "what_to_verify": "string",
      "source_ids": ["string"]
    }
  ],
  "portfolio_note": "string"
}
Validate the response. If it fails validation or Sarvam is unavailable, show deterministic, pre-written explanation templates. Do not display unvalidated free-form legal conclusions.
7. UI requirements for Nominee 360
Add a Nominee 360 or Portfolio Nominee Check view within Active Insurances.

Display:
1. Portfolio summary: number of policies analysed, number with nominee details found, number with unconfirmed registration, number of review flags.
2. A per-policy table/card showing policy type, insurer, masked policy ID, nominee name as recorded, linked mock profile candidate, source type and registration status.
3. A finding list with severity, evidence, explanation and action.
4. A Review finding control with outcomes:
   - Reviewed — no change needed (retain finding and user note)
   - Correct demo data (only update local synthetic fixture after explicit confirmation)
   - Intentionally different nominees (close only the portfolio-variation finding)
   - Ask insurer / unresolved (keep open)
5. A downloadable portfolio report containing findings and source provenance, marked DEMO ANALYSIS — NOT AN INSURER OR LEGAL DETERMINATION.
Never present one overall percentage as a legal readiness score. If a completeness indicator is used, name it Data completeness and explain its calculation.
Part B — AI Family Claim Orchestrator: One Event, Multiple Policies
8. User journey
Integrate this into the existing Phase 4 Family Claims flow. Do not create a new family access path.

Precondition: the current demo claimant has an existing family case with the simulated access-review gate completed. If access is not granted, the policy list and claim orchestrator must remain unavailable.
Orchestration flow
1. Claimant opens an approved demo FamilyCase.
2. Selects/records the event: Death of the policyholder / insured person, event date and minimum synthetic context.
3. Load all policies linked to the deceased demo profile that the current access approval permits.
4. For every policy, identify the policyholder, insured person, product type, policy period, coverage sections, nominee record, assignment/lender indicators and evidence provenance.
5. Run deterministic event-to-policy relevance rules. Do not assume every policy creates a death benefit.
6. Create a single parent FamilyClaimBatch and one child PolicyClaimWorkflow per relevant or potentially relevant policy.
7. For each child workflow, retrieve a product-specific versioned checklist fixture and identify common documents that may be reusable.
8. Sarvam-105B explains the overall plan and each policy-specific next step using the structured rule outputs.
9. The claimant reviews and confirms which child workflows to create. The backend creates them only after explicit confirmation.
10. The shared dashboard tracks each workflow independently. Claim status must be user-entered or labelled simulated; no insurer status is implied.
9. Critical event relevance rules — avoid false death claims
A death event does not make every insurance policy a death-benefit claim. Implement a deterministic rule matrix, configurable in fixtures.
Policy type	Potential route	Required checks before creating claim-preparation workflow
Life insurance	Potential death-benefit claim	Deceased must match the life insured; policy/event dates and death benefit evidence must be present. Insurer decides cover and entitlement.
Personal accident	Potential accidental-death benefit	Only if the policy contains an applicable accidental-death cover and the supplied event information may fall within its definition. Otherwise show Event relevance needs insurer review.
Credit-life / loan protection	Credit-life claim enquiry	Check that the deceased is the insured borrower and the demo record indicates a linked loan/assignment. Explain that proceeds may be applied against outstanding loan according to the contract; never say the loan is cleared.
Health insurance	Not a death benefit by default	Create an Outstanding medical expense claim enquiry only if there are uploaded/seeded eligible treatment expenses incurred before death or another clearly documented benefit. Do not create a death-benefit claim merely because the policyholder died.
Motor insurance	Only applicable accident-related sections	Check for owner-driver personal accident or relevant third-party liability facts and policy wording. A standard motor policy is not automatically a death-benefit policy.
Other / unknown	Review only	Show Product/event relevance requires insurer confirmation; do not invent a claim type.


Use explicit event_relevance values:
- POTENTIAL_LIFE_DEATH_CLAIM
- POTENTIAL_ACCIDENTAL_DEATH_BENEFIT
- CREDIT_LIFE_ENQUIRY
- OUTSTANDING_MEDICAL_EXPENSE_ENQUIRY
- MOTOR_ACCIDENT_COVER_REVIEW
- NOT_INDICATED_BY_AVAILABLE_RECORDS
- INSUFFICIENT_EVIDENCE
The LLM cannot assign or override these values. It can only explain the rule engine's output and evidence.
10. Per-policy claim workflow
Each child workflow must be independent and include:
- Policy display details and masked policy number.
- Insurer and product type.
- Why the policy was included in the family batch.
- Event relevance status with evidence.
- Nominee details and nomination provenance/status, if any.
- Claimant capacity as currently declared/recorded (e.g. RECORDED_NOMINEE_IN_DEMO, AUTHORISED_REPRESENTATIVE_DEMO, LEGAL_HEIR_CLAIMANT_UNVERIFIED, OTHER, UNSURE).
- A separate warning that this capacity label is not legal proof or insurer approval.
- Versioned policy/product-specific checklist.
- Common documents available for reuse.
- Policy-specific documents still required.
- Editable draft communication.
- User-entered submission and follow-up dates.
- Timeline and case status.
- Source and last-reviewed timestamp.
Suggested child workflow states:

DISCOVERED → RELEVANCE_REVIEW → CHECKLIST_READY → DOCUMENTS_IN_PROGRESS → READY_FOR_USER_REVIEW → DRAFT_PREPARED → USER_MARKED_SUBMITTED → FOLLOW_UP → USER_MARKED_RESOLVED

If the user records a rejection or further document request, move to INSURER_QUERY_RECORDED and offer the existing Claims Saathi. Do not invent a settlement status.
11. Common document intelligence
Create a parent document index for the family case. Do not make a document available to every insurer workflow automatically.

Common document categories may include:
- Death certificate.
- Claimant identity proof.
- Relationship proof, if required.
- Policy schedule/certificate.
- Bank proof, where specifically required.
- Legal-heir/succession/probate/authority documents, where the insurer's case-specific checklist requires them.
- Medical records or treatment bills where an outstanding medical claim is relevant.
- Accident evidence or FIR/post-mortem records only where relevant to the policy/event and requested by the applicable insurer.
For each document:
- Record source, type, extracted fields, confidence/source pages and review state.
- Keep the uploaded original subject to the existing Phase 2/3 privacy/retention policy; do not persist it or log its contents if the existing app is configured for in-memory-only handling.
- Let the claimant choose which child workflows may reference the document.
- Show that each insurer may require its own original, attested copy, prescribed form or submission channel.
- Do not claim that one uploaded copy will be accepted by all insurers.
Use Sarvam Document AI Extract for structured fields when an authorised synthetic document is uploaded. Reuse the existing adapter and job polling. Do not use Sarvam-105B vision/chat as a substitute for Document AI OCR.
12. Claim checklist and source grounding
Do not let Sarvam invent insurer document requirements.

Create versioned local JSON fixtures for the hackathon, for example:
- data/claim_playbooks/life_death_demo_v1.json
- data/claim_playbooks/personal_accident_death_demo_v1.json
- data/claim_playbooks/credit_life_enquiry_demo_v1.json
- data/claim_playbooks/health_outstanding_expense_demo_v1.json
- data/claim_playbooks/motor_accident_review_demo_v1.json
Each playbook should include:
- Product / event type.
- Applicability conditions.
- Required or commonly requested documents (clearly labelled as demo checklist, not universal rule).
- Conditional documents and their triggering conditions.
- Source URL/title and last-reviewed date.
- Version number.
- A confirm_with_insurer flag for uncertain items.
For the prototype, use synthetic, insurer-neutral checklists unless verified public insurer documentation is already available in the repository. Do not create fake insurer-specific requirements. Display Illustrative checklist — confirm with the insurer wherever a rule is not sourced from the actual policy/insurer.

Sarvam should receive retrieved excerpts and the playbook source IDs, not a vague prompt to write a checklist from memory.
13. AI role and tool allowlist for the Claim Orchestrator
Use existing Sarvam-105B integration. The model may summarise, explain, ask clarifying questions and call only allowlisted functions.

Suggested functions:
Read-only functions
1. get_family_case_summary(family_case_id) — current claimant's permitted family case only.
2. get_deceased_demo_profile(deceased_profile_id) — only after family access status is approved in the mock backend.
3. get_policies_for_family_case(family_case_id) — returns redacted policy records from the permitted deceased demo profile.
4. get_nominee_consistency_report(family_case_id) — returns deterministic findings and source references.
5. classify_policy_event_relevance(policy_id, event_type, event_date) — runs the deterministic policy/event rule matrix; returns evidence and status.
6. get_claim_playbook(policy_id, event_relevance) — retrieves a versioned, applicable playbook.
7. get_shared_document_index(family_case_id) — returns document metadata/categories only, not raw file bytes.
8. get_policy_claim_workflow(workflow_id) — returns only a workflow accessible to the current family claimant.
Write functions — require explicit user action
9. create_family_claim_batch(family_case_id, selected_policy_ids, event_details) — must validate the family access gate and current-user permission. Present a preview and require the user to press Create claim workflows before calling it.
10. mark_document_for_workflow(document_id, workflow_id) — only after the user chooses the document and target workflow.
11. add_claim_timeline_event(workflow_id, event_type, event_date, note) — only after user confirmation; label entries as User reported.
12. save_claim_draft(workflow_id, draft_text) — save editable draft only; no sending/submission endpoint.
All function arguments must be strictly schema-validated (Pydantic/Zod, extra=forbid), and each function must independently enforce session, family-case and workflow ownership. Never trust model-supplied IDs or permission flags.
14. UI requirements
14.1 Nominee 360 screen
Include:
- Analyse my portfolio button.
- Portfolio totals.
- Linked demo family profiles area with consent status.
- Per-policy comparison table/cards.
- Name/DOB/relationship/minor/appointee/allocation findings.
- Source provenance: Policy OCR, User entered, Mock linked profile, Mock insurer acknowledgement.
- Clear distinction between Different nominees across policies (information) and actual data inconsistency (attention).
- Review, Mark intentionally different, Ask insurer and Correct demo record controls.
- An explanation panel generated from Sarvam-105B, with deterministic fallback.
14.2 Family Claim Orchestrator screen
Within an approved Family Claims case, add:
- Event details summary.
- Analyse policies for this event action.
- A policy matrix showing insurer/product, insured person, nomination source/status, event relevance and recommended next step.
- A clear separation between potential death-benefit claims, accident-related enquiries, credit-life enquiries, outstanding medical-expense enquiries and policies with no indicated death-related route.
- Create selected claim workflows button with a preview of all child workflows.
- Parent family case dashboard with one card per child workflow.
- Child workflow detail view: evidence, checklist, document mapping, draft, timeline and user-entered status.
- A shared document panel with explicit workflow selection.
14.3 Visual and language rules
- Maintain the existing Paytm-inspired demo visual style, but label all Paytm elements as simulated.
- Use neutral labels: Potential issue, Needs review, Not found in uploaded document, Insurer confirmation needed.
- Do not show red error styling for all nominee variations. A different nominee on another policy is not inherently a problem.
- Do not display a legal eligibility score or a claim approval probability.
Part C — Data model and persistence
15. Extend existing tables/models; do not duplicate them
Inspect the current database/models first. Adapt to the existing naming and ORM.
15.1 Nominee profile snapshot
{
  "id": "internal_uuid",
  "demo_paytm_user_id": "paytm.demo.meera",
  "display_name": "Meera Sharma",
  "legal_name_demo": "Meera R Sharma",
  "date_of_birth": "1991-04-12",
  "relationship_to_policyholder": "SPOUSE",
  "family_link_status": "ACCEPTED",
  "profile_sharing_consent": true,
  "consented_fields": ["legal_name_demo", "date_of_birth", "relationship_to_policyholder"],
  "demo_only": true
}
15.2 Nominee consistency report
{
  "id": "internal_uuid",
  "owner_demo_user_id": "user_demo_001",
  "created_at": "ISO-8601",
  "analysis_version": "nominee-check-v1",
  "policy_ids": ["pol_001", "pol_002"],
  "findings": [],
  "overall_status": "REVIEW_AVAILABLE",
  "demo_only": true
}
15.3 Family claim batch
{
  "id": "internal_uuid",
  "family_case_id": "family_case_001",
  "claimant_demo_user_id": "user_demo_002",
  "deceased_demo_profile_id": "profile_demo_001",
  "event_type": "DEATH",
  "event_date": "2026-10-01",
  "access_status": "SIMULATED_ACCESS_GRANTED",
  "status": "DRAFT",
  "child_workflow_ids": [],
  "demo_only": true
}
15.4 Policy claim workflow
{
  "id": "internal_uuid",
  "batch_id": "batch_001",
  "policy_id": "pol_001",
  "event_relevance": "POTENTIAL_LIFE_DEATH_CLAIM",
  "relevance_evidence": [],
  "claimant_capacity": "RECORDED_NOMINEE_IN_DEMO",
  "claimant_capacity_verification": "UNVERIFIED_BY_INSURER",
  "playbook_id": "life_death_demo_v1",
  "documents": [],
  "status": "CHECKLIST_READY",
  "timeline": [],
  "demo_only": true
}
Use internal UUIDs as primary keys. Do not use name, policy number or Paytm-style ID as database primary keys.
Part D — Seeded demo scenario
16. Required demo data
Seed at least three mock users:
- paytm.demo.aarav — deceased policyholder for the demo.
- paytm.demo.meera — adult spouse and linked family claimant.
- paytm.demo.riya — minor child nominee.
Use fictional names, DOBs and policy references. Ensure the data is internally consistent with the expected outputs below.

Seed at least five policy records for Aarav:
Policy	Product	Nominee fixture	Expected analysis / event route
P1	Life insurance	Meera Sharma, DOB 1991-04-12, spouse, 100%	Name variation against linked profile if seeded as Meera R Sharma; potential life death-claim workflow
P2	Life insurance	Riya Sharma, DOB 2012-03-04, daughter, 100%, appointee missing	Minor nominee/appointee review; potential life death-claim workflow
P3	Life insurance	Rajesh Sharma, parent, 100%	Different nominee from P1/P2; show as informational/intentional variation, not an error; potential life death-claim workflow
P4	Health insurance	Nominee not visible in uploaded schedule	Do not state no nominee exists; only NOT_FOUND_IN_DOCUMENT; death itself does not create a death-benefit claim; optionally seeded unpaid medical expense gives an outstanding-expense enquiry
P5	Credit-life / loan protection	Meera listed in demo record; lender assignment/loan reference present	Credit-life enquiry; explain insurer/lender must determine cover and any outstanding balance


Optionally add a motor policy with owner-driver personal accident cover and a seeded accident event to demonstrate the conditional branch. Do not make motor produce a death claim when no relevant accident facts/cover exist.

For linked-profile lookup:
- Meera's mock profile returns Meera R Sharma, DOB 1991-04-12, relationship SPOUSE, accepted link and field-level consent.
- Riya's mock profile returns DOB 2012-03-04, relationship DAUGHTER, accepted link and field-level consent.
- Rajesh may be linked to the owner as PARENT with consent.
The demo should show:
1. P1 name variation is presented as a possible match, not a mismatch or identity proof.
2. P2 is a minor nominee as of the seeded event date. For the life-policy route, show an appointee review flag and explain that a minor is not automatically ineligible.
3. P3's different nominee is an intentional portfolio variation, not an error.
4. P4's missing nominee field in the uploaded schedule is not proof that no nomination exists.
5. The orchestrator creates distinct workflows only for relevant claims/enquiries and does not pretend every one of the five policies pays on death.
6. The parent batch dashboard shows each child workflow separately.
Part E — Security, privacy and compliance guardrails
17. Mandatory rules
- This is a synthetic-data hackathon prototype. Do not use real personal, health, financial, death-certificate or policy data.
- Paytm is mock-only; never connect to Paytm services.
- Only show linked nominee profile attributes when the demo link is accepted and field-level consent is true.
- No OTP, PIN, password, Aadhaar, PAN, bank account or payment credentials.
- Never expose policy information before the existing Phase 4 family access gate succeeds.
- The LLM cannot approve family access, authenticate a death certificate, determine heirship, decide legal entitlement, or approve/deny/settle claims.
- Never call a nominee ineligible based solely on being under 18.
- Never assume a different nominee across policies is wrong.
- Never treat OCR missing data as proof that a nominee does not exist.
- Never infer legal relationship from surname or LLM analysis.
- Never infer that a life, motor, health or credit-life policy automatically creates a death benefit.
- Never claim that a loan is cleared by a credit-life policy.
- All claim checklists must be sourced from versioned local playbooks and/or the specific policy. Unsourced items must say Confirm with insurer.
- User must explicitly confirm before a family batch or child workflows are created.
- No insurer form submission, email dispatch, payment, cancellation or live claim-status API in this build.
- Keep API keys in .env; never in frontend code or logs.
- Do not log original documents, full policy identifiers, profile DOBs or raw OCR text.
18. Regulatory interpretation notes to encode carefully
These are product guardrails, not legal advice:
1. Life nominee minor: Section 39(1) of the Insurance Act, 1938 contemplates a minor nominee and permits the policyholder to appoint a person in the insurer's prescribed manner to receive money during the nominee's minority. Do not flag the minor as automatically ineligible. See India Code Act text: https://www.indiacode.nic.in/bitstream/123456789/2304/1/A1938-04.pdf
2. Registration evidence: Section 39 also addresses communication/registration of nominations and written acknowledgement by the insurer. Therefore Paytm mock-link acceptance or OCR extraction is not insurer registration. Use the correct source status. Same Act link above.
3. General and health insurance nomination: IRDAI (Protection of Policyholders' Interests, Operations and Allied Matters of Insurers) Regulations, 2024 include nomination provisions for life, general and health insurers, but do not assume the detailed Section 39 life-insurance minor/appointee mechanics automatically apply to every product. Use insurer/product-specific rules. Official Gazette PDF: https://financialservices.gov.in/beta/sites/default/files/2024-11/IRDAI%20%28Protection%20of%20%20Policyholder%27s%20Interests%2C%20operations%20and%20allied%20matters%20of%20insurers%29%20Regulations%2C%202024.pdf
4. Age of majority: Section 3 of the Majority Act, 1875 states 18 for persons domiciled in India, subject to the Act's scope and applicable law. Treat age as an attention flag; do not decide eligibility. Official India Code: https://www.indiacode.nic.in/bitstream/123456789/15299/1/majorityact.pdf
5. Beneficial entitlement: Section 39(7) distinguishes specified life-policy nominees (parents, spouse, children or combinations) from other nominees for beneficial entitlement, subject to the statutory qualifications. Do not infer beneficial ownership or legal entitlement in the product. Refer the claimant to insurer/legal advice when relevant.
6. Claim types: Policy wording and the insured event determine the possible benefit. A death event alone does not turn every health or motor policy into a death-benefit claim.
Have an appropriate legal/compliance reviewer validate any real-world deployment. The hackathon prototype must not claim to be legally certified or compliant for production use.
Part F — Tests and definition of done
19. Nominee intelligence acceptance tests
- [ ] Portfolio analysis loads every policy for the current demo owner and no other user's policies.
- [ ] Mock linked profile lookup is blocked until link accepted and required field consent granted.
- [ ] Profile DOB/legal name is hidden when consent is missing or withdrawn.
- [ ] MEERA SHARMA vs MEERA R SHARMA is flagged as a possible name variation with both sources shown; no auto-merge.
- [ ] A DOB mismatch creates a review finding.
- [ ] A relationship mismatch creates a review finding only when both values are explicitly present.
- [ ] A minor nominee on a life policy creates an appointee review flag when DOB/event date indicate minority and appointee details are absent.
- [ ] The minor is never labelled INELIGIBLE by default.
- [ ] The same minor data on a general/health policy does not automatically apply the life-policy Section 39 rule; it returns product-rule confirmation required.
- [ ] Different nominees on different policies are shown as an informational variation, not an error.
- [ ] An OCR field not found in the document does not become NO_NOMINEE_EXISTS.
- [ ] Allocation total is checked only when explicit percentages exist.
- [ ] The LLM cannot change severity or status.
- [ ] Findings can be reviewed/closed only through explicit user actions and are audit logged.
20. Claim orchestrator acceptance tests
- [ ] Orchestrator is unavailable until the Phase 4 simulated family-access gate is approved.
- [ ] A family batch can be previewed before creation.
- [ ] No batch or child workflow is created until the claimant explicitly confirms.
- [ ] Life policy linked to the deceased as life insured creates a potential death-claim workflow when fixture rules apply.
- [ ] Accident policy with no supporting accidental event does not get an assumed death-benefit workflow.
- [ ] Credit-life policy creates an enquiry, not a guarantee that the loan is cleared.
- [ ] Health policy does not automatically create a death-benefit workflow; only a seeded/recorded outstanding medical expense can create an enquiry.
- [ ] Standard motor policy does not automatically create a death-benefit workflow.
- [ ] Each relevant policy has a separate child workflow, checklist, source, status and timeline.
- [ ] Common documents are not automatically shared to all child workflows; user selects the destinations.
- [ ] Claim checklist items come from versioned playbooks; the LLM cannot invent requirements.
- [ ] Family claimant can see only the parent batch and child workflows associated with their approved family case.
- [ ] User-reported status remains labelled User reported or Demo status; it is not shown as insurer-confirmed.
- [ ] Sarvam timeout/error does not block deterministic workflow creation or show a fake answer.
21. Basic automated tests
Add unit tests for:
- Name normalisation and fuzzy candidate scoring.
- DOB parsing and age on event date (including exact 18th birthday boundary).
- Minor nominee flag and appointee presence.
- Product-specific rule guard: life vs general/health.
- Relationship mismatch requiring two explicit values.
- Allocation sum calculation.
- Missing OCR field vs explicit insurer-recorded no-nominee status.
- Policy/event relevance matrix.
- Family-case permission checks.
- Sarvam JSON schema validation and malformed model response fallback.
- User confirmation required before write functions.
Add one end-to-end demo test for the seeded scenario in Section 16.
Part G — Suggested implementation order
22. Implement in this order
1. Inspect and map existing code. Identify current policy, nominee, mock Paytm profile, FamilyCase, document, Sarvam adapter and claims tables. Do not duplicate them.
2. Build deterministic nominee comparison first. Implement name/DOB/relationship/age/appointee/allocation/source-status rules and unit tests before adding LLM explanations.
3. Add consent-gated mock profile lookup. Reuse the current Paytm user switcher/directory; enforce link acceptance and field-level consent server-side.
4. Add Nominee 360 UI. Show per-policy evidence, findings, source, severity and review actions.
5. Add Sarvam-105B explanation. Send only redacted findings. Validate response schema. Keep deterministic fallback.
6. Build policy/event relevance matrix. Add product-specific rules and tests. Do not use the LLM to decide whether an event is covered.
7. Build FamilyClaimBatch and child workflows. Reuse the existing Phase 4 family access gate and policy inventory.
8. Add common document index and per-policy document mapping. Keep explicit user approval for each target workflow.
9. Add playbook retrieval and claim explanations. Use versioned fixtures and source links.
10. Add parent/child dashboard and final end-to-end test. Confirm all states survive refresh using the existing persistence layer.
23. Demo walkthrough
Demo A — Cross-Policy Nominee Intelligence
1. Login as paytm.demo.aarav.
2. Open Active Insurances → Nominee 360.
3. Show three linked demo family profiles and their consent statuses.
4. Run analysis across five seeded policies.
5. Show the spouse name variation and linked-profile match candidate.
6. Show the minor daughter flag: Appointee details need review — explicitly explain that minor does not mean ineligible.
7. Show the parent nominee on another policy as an intentional difference, not an error.
8. Show one policy where nominee details were not found in the uploaded schedule; explain that this does not prove no nominee exists.
9. Open a Sarvam-generated plain-language explanation with supporting source data.
10. Mark one finding as reviewed; show it in the audit/history.
Demo B — One Death, Multiple Claims
1. Login as paytm.demo.meera.
2. Open the existing simulated Family Claims case and confirm access has passed the mock review gate.
3. Open Analyse policies for this event and select the seeded death event.
4. Show the policy relevance matrix: life claims, minor nominee/appointee review, credit-life enquiry, health outstanding-expense enquiry or no indicated route.
5. Preview all child workflows and their reasons.
6. Confirm Create selected claim workflows.
7. Open the parent family dashboard and then two individual child workflows.
8. Show one shared death certificate mapped by the user to selected workflows, and different insurer-specific checklist items.
9. Ask Sarvam-105B to explain what the family should do next.
10. Update one timeline entry as User reported; show that it is not labelled as insurer-confirmed.
Part H — Completion report required from OpenCode
24. OpenCode must finish by reporting
- Files added/modified.
- Existing Phase 1–4 functions preserved.
- New pages/routes and services implemented.
- Environment variables required (reuse the current Sarvam key; no Paytm credentials).
- Tests run and results.
- Exact commands to start the app.
- Any unimplemented acceptance criteria and why.
- A 2–3 minute walkthrough of the two capabilities.
- Explicit confirmation that Paytm is mock-only and no live insurer submission/status API was added.
OpenCode execution prompt
Read this entire specification and inspect the existing repository and prior phase specifications. Implement only the two capabilities in this document as an incremental extension. Preserve existing Phase 1–4 functionality. Paytm must remain mock-only. Implement deterministic nominee consistency checks first, then Sarvam-105B explanations, then the policy/event rule matrix and multi-policy family claim batch. Do not let the LLM determine legal eligibility, authenticate documents, grant access, or decide whether a policy pays on death. Do not label minor nominees as ineligible by default. Build the acceptance tests, run the application and fix regressions. Keep all demo data synthetic and make the finished flows genuinely usable end-to-end.

Official references
- Sarvam Chat Completions, sarvam-105b, tool calling and structured output: https://docs.sarvam.ai/api/token-factory/chat-completions
- Sarvam Document AI Extract API: https://docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/how-to/extract
- Insurance Act, 1938, Section 39 (India Code): https://www.indiacode.nic.in/bitstream/123456789/2304/1/A1938-04.pdf
- IRDAI (Protection of Policyholders' Interests, Operations and Allied Matters of Insurers) Regulations, 2024 (Official Gazette PDF): https://financialservices.gov.in/beta/sites/default/files/2024-11/IRDAI%20%28Protection%20of%20%20Policyholder%27s%20Interests%2C%20operations%20and%20allied%20matters%20of%20insurers%29%20Regulations%2C%202024.pdf
- Majority Act, 1875, Section 3 (India Code): https://www.indiacode.nic.in/bitstream/123456789/15299/1/majorityact.pdf
End of specification.