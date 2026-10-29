"""Static English/Hindi UI strings and safety-critical copy.

The app never machine-translates policy clauses, legal instructions or safety
copy at runtime. These strings are reviewed, static fixtures. Hindi text is
provided for the key labels, instructions, status wording and disclaimers.
"""

from __future__ import annotations

from src.models import Language

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Virasat Saathi",
        "app_tagline": "Financial guidance when you need it. Support when it matters most.",
        "independent": "Independent hackathon prototype",
        "prototype_label": "Independent hackathon prototype · Demo data",
        "demo_data_label": "DEMO DATA",
        "privacy_banner": (
            "Hackathon prototype — use the fictional demo case. Do not upload real medical, "
            "insurance, banking or deceased-person records."
        ),
        "language_label": "Language",
        "reset_demo": "Reset demo",
        "reset_help": "Clears this session and returns to the synthetic demo case.",
        "home_heading": "What would you like help with?",
        "home_sub": (
            "Two calm, evidence-first journeys. The prototype explains and prepares; "
            "it does not decide coverage, ownership or claim approval."
        ),
        "claims_card_title": "Claims Companion",
        "claims_card_desc": (
            "Help me prepare or follow up on an insurance claim. Use a fictional health "
            "reimbursement case with a clause-cited demo policy, checklist, draft and tracker."
        ),
        "claims_card_cta": "Open Claims Companion",
        "family_card_title": "Family Finance Finder",
        "family_card_desc": (
            "Help me find financial leads and next steps after a loss. Scan a synthetic "
            "statement for possible insurance, investment, loan or subscription clues."
        ),
        "family_card_cta": "Open Family Finance Finder",
        "home_trust_note": (
            "AI explains and assists. Deterministic rules check. Official sources establish "
            "requirements. The user decides."
        ),
        "journey_01": "Journey 01 · Claims",
        "journey_02": "Journey 02 · Family",
        "back_home": "← Back to home",
        "footer_note": (
            "Independent hackathon prototype. Not affiliated with Paytm, any insurer, IRDAI, "
            "RBI or Sarvam AI. Not a legal opinion or compliance certification."
        ),
        "footer_rule": "The model explains; the rules check; the institution decides.",

        "claims_heading": "Claims Companion",
        "claims_sub": (
            "Prepare a fictional health reimbursement claim, see the source behind every item, "
            "draft a follow-up and keep your own next steps."
        ),
        "demo_case_label": "DEMO CASE",
        "load_demo_claim": "Load demo claim",
        "reload_demo": "Reload demo claim",
        "demo_loaded": "Demo case loaded",
        "claim_overview": "Claim overview",
        "product_label": "Product",
        "claim_type_label": "Claim type",
        "claim_type_value": "Reimbursement after hospital discharge",
        "claim_state_label": "Demo claim state",
        "claimant_label": "Claimant",
        "hospital_label": "Hospital",
        "policy_label": "Policy",
        "checklist_source_label": "Checklist source",
        "claims_disclaimer": (
            "This app does not decide policy coverage, claim approval, payout or eligibility. "
            "It is an information and preparation assistant, not an insurer, broker, TPA, "
            "lawyer, doctor or surveyor."
        ),
        "policy_facts_title": "Policy and claim facts",
        "policy_facts_sub": (
            "Every statement below is from the fictional demo policy and carries a clause ID "
            "and page. The wording is cautious: the demo policy text says…, not you are covered."
        ),
        "policy_lookup_label": "Look up a topic in the demo policy",
        "policy_lookup_help": (
            "This prototype only answers from the included fictional fixture. It cannot verify "
            "your real policy. If a topic is not present, it says so and links the insurer route."
        ),
        "choose_topic": "Choose a topic",
        "policy_source_caption": "Source: fictional demo policy fixture",
        "clause_label": "Clause",
        "page_label": "page",
        "synthetic_sample_wording": "Synthetic sample wording — not an actual policy.",
        "not_verified": "Not verified in the available information.",
        "insurer_link_cta": "Open the official insurer/regulator route",
        "checklist_title": "Document checklist",
        "checklist_sub": (
            "These categories come from data/demo_claim.json. They are illustrative for this "
            "fictional case, not a universal checklist for every insurer or product."
        ),
        "checklist_validation_note": (
            "Checking an item means only that you marked it provided. The prototype does not "
            "validate authenticity, correctness or sufficiency, and it does not imply that the "
            "insurer will accept the document or the claim."
        ),
        "status_not_marked": "Not marked",
        "status_marked_provided": "Marked provided",
        "status_needs_confirmation": "Need to confirm with insurer",
        "why_listed": "Why this is listed",
        "source_id_label": "Source ID",
        "checklist_progress_marked": "Marked provided",
        "checklist_progress_remaining": "Still unmarked",
        "checklist_progress_confirm": "Need to confirm with insurer",
        "checklist_progress_caption": (
            "Counts are deterministic from your checkboxes. Complete means checklist marking "
            "only; it never means the claim is approved or the documents are sufficient."
        ),
        "reset_checklist": "Clear checklist markings",
        "draft_title": "Help me respond",
        "draft_sub": (
            "Generate a deterministic draft using only the fictional demo case fields and "
            "checklist category names. Review and edit it before copying or downloading."
        ),
        "draft_kind_label": "Draft type",
        "draft_missing_label": "Missing document category",
        "generate_draft": "Generate draft",
        "draft_review_label": "I have reviewed this draft. I understand it is a draft and I will send it myself.",
        "download_draft": "Download draft (.txt)",
        "draft_no_submission": (
            "No email, WhatsApp, insurer API or portal submission is implemented. Nothing is "
            "sent anywhere. Copy or download the draft and send it yourself through the "
            "insurer's official channel."
        ),
        "draft_demo_only": "DEMO DRAFT — fictional case only. Edit before use.",
        "draft_empty": "Choose a draft type and select Generate draft.",
        "draft_kind_missing": "Missing document follow-up",
        "draft_kind_status": "Ask for claim status",
        "draft_kind_additional": "Respond to a request for more information",
        "draft_kind_grievance": "Prepare an insurer grievance",
        "tracker_title": "Track next steps",
        "tracker_sub": (
            "A session-only timeline. Enter a reminder date only if the insurer stated one. "
            "The prototype does not calculate or infer a legal or regulatory deadline."
        ),
        "due_date_label": "Reminder date stated by the insurer (optional)",
        "due_date_help": "Use YYYY-MM-DD. Leave blank if no date was stated.",
        "notes_label": "Notes",
        "mark_done": "Mark done",
        "tracker_progress": "steps marked done",
        "escalation_title": "Escalation help",
        "escalation_sub": (
            "Plain-language routes only. The prototype does not file complaints, decide "
            "eligibility or encode unverified deadlines."
        ),
        "escalation_step_1": (
            "First contact the insurer's official Grievance Redressal Officer through the "
            "insurer's official channel. Keep the written acknowledgement."
        ),
        "escalation_step_2": (
            "If the matter remains unresolved or the response is unsatisfactory, check the "
            "current Bima Bharosa process on the official source."
        ),
        "escalation_step_3": (
            "Check current Ombudsman eligibility and process on the Council for Insurance "
            "Ombudsmen source. Requirements can vary; nothing here is a legal conclusion."
        ),
        "escalation_links_title": "Official escalation links",
        "anti_fraud_title": "Payment and fraud warning",
        "anti_fraud_warning": (
            "Never pay a fee to receive claim proceeds. Never scan a QR code sent by a "
            "stranger. Never share an OTP, UPI PIN, password or card PIN. IRDAI/Bima Bharosa "
            "does not ask complainants for payment to resolve a grievance."
        ),
        "case_summary_title": "Download demo case summary",
        "case_summary_sub": (
            "A local, in-memory text summary with a DEMO watermark. It is not an insurer "
            "decision, legal advice or proof of coverage."
        ),
        "download_case_summary": "Download demo summary (.txt)",
        "local_doc_title": "Local document readability check (optional)",
        "local_doc_sub": (
            "Optional, local-only PDF/TXT readability aid. It does not verify authenticity, "
            "sufficiency, coverage or claim eligibility, and it is never sent to Sarvam."
        ),
        "upload_ack_label": (
            "I understand this prototype is for fictional demo data only. If I choose a local "
            "file, it stays in memory, is never sent to Sarvam, and I will not upload real "
            "medical, insurance or banking records."
        ),
        "upload_doc": "Choose a local PDF or TXT file",
        "upload_doc_help": "PDF, TXT only · 10 MB maximum · processed in memory · not saved",
        "pdf_ocr_note": "OCR is not supported. Scanned/image-only PDFs cannot be read here.",
        "pdf_readable": "Selectable text found",
        "pdf_not_readable": "No readable text found",
        "uploaded_doc_ai_disabled": "AI is disabled for user-supplied documents in this prototype.",
        "sarvam_switch_label": "Use Sarvam AI for fictional demo content only",
        "sarvam_switch_help": (
            "Optional. The demo works fully without it. AI never sees your free text, "
            "uploaded files or transaction rows."
        ),
        "sarvam_ai_note": (
            "AI-generated explanation of fictional demo content. Verify all requirements "
            "with your insurer."
        ),
        "sarvam_disabled_note": (
            "Deterministic explanation. Sarvam is not configured or is switched off."
        ),
        "sarvam_fallback_note": (
            "Sarvam was unavailable or returned unusable text, so this deterministic "
            "explanation is shown."
        ),
        "sarvam_source_label": "Fixed synthetic source excerpt",
        "sarvam_verify_note": (
            "The original checklist remains visible and authoritative for this demo. AI copy "
            "never creates a requirement, deadline or eligibility decision."
        ),
        "sarvam_status_label": "Sarvam status",
        "sarvam_status_disabled": "Off — deterministic mode",
        "sarvam_status_no_key": "Off — no API key configured",
        "sarvam_status_deprecated_model": "Off — deprecated model ID configured",
        "sarvam_status_bad_url": "Off — base URL must use https",
        "sarvam_status_ready": "Configured — optional fictional-content mode",
        "fallback_claim_form": (
            "The demo checklist lists a completed claim form. Marking it provided only "
            "records your own note; it does not validate the form. Confirm the insurer's "
            "actual requirement with the insurer."
        ),
        "fallback_discharge_summary": (
            "The demo checklist lists the hospital discharge summary. Marking it provided "
            "only records your own note; it does not verify the document or imply insurer "
            "acceptance. Confirm the insurer's actual requirement."
        ),
        "fallback_itemised_bill": (
            "The demo checklist lists the itemised final hospital bill. Marking it provided "
            "only records your own note. The prototype does not check the bill or decide "
            "whether any amount is payable."
        ),
        "fallback_payment_receipt": (
            "The demo checklist lists payment receipts. Marking them provided only records "
            "your own note. Confirm with the insurer which receipts it wants and in what form."
        ),
        "fallback_policy_schedule": (
            "The demo checklist lists the policy schedule. Marking it provided only records "
            "your own note. The prototype does not verify the schedule or decide coverage."
        ),
        "fallback_supporting_reports": (
            "The demo policy says the insurer may ask for prescriptions or investigation "
            "reports where relevant. Confirm whether the insurer wants them for this claim; "
            "this prototype does not decide medical necessity."
        ),
        "sarvam_request_button": "Get AI explanation",
        "sarvam_choose_category": "Checklist category for the AI explanation",
        "sarvam_not_requested": (
            "Deterministic explanation shown. Use the button to request an optional AI "
            "paraphrase of the fictional source excerpt."
        ),
        "due_date_invalid": "Use YYYY-MM-DD, or leave the reminder blank.",
        "no_official_link": (
            "No official portal is linked for this lead. Verify with the institution using "
            "its official contact details."
        ),
        "family_no_ai_note": (
            "Family Finance Finder uses deterministic matching only. No AI model is called "
            "for transaction rows."
        ),
        "local_upload_label": "LOCAL UPLOAD — synthetic data only",
        "statement_rows_title": "Statement rows used for matching",
        "uploaded_file_processed": "File processed locally in memory. Nothing was saved.",
        "statement_rows_metric": "Statement rows",
        "recurring_patterns_metric": "Recurring patterns",
        "choose_csv": (
            "Choose a CSV file above to see possible leads. The file is processed locally "
            "in memory and never sent to Sarvam."
        ),
        "table_row": "row",
        "table_date": "date",
        "table_description": "description",
        "table_amount": "amount",
        "table_direction": "direction",
        "page_word": "Page",
        "row_word": "row",
        "ai_generated_label": "AI-GENERATED",
        "footer_license": "MIT-licensed prototype code · Synthetic fixtures only.",
        "fixture_error": "The fictional demo fixture failed validation",

        "family_heading": "Family Finance Finder",
        "family_sub": (
            "Read a synthetic transaction statement, find possible financial clues, and see the "
            "exact rows that caused each match. Every result is a lead, never proof."
        ),
        "synthetic_data_label": "SYNTHETIC DATA",
        "load_synthetic": "Load synthetic statement",
        "statement_mode_label": "Statement source",
        "mode_demo": "Included synthetic statement",
        "mode_upload": "Upload a CSV (local only)",
        "upload_csv_label": "Choose a local CSV statement",
        "upload_csv_help": "CSV only · 10 MB maximum · processed in memory · not saved",
        "upload_local_note": (
            "The CSV is parsed locally in memory. Rows are never written to disk, logged or "
            "sent to Sarvam or any external service."
        ),
        "ai_disabled_upload": "AI is disabled for user-supplied records in this prototype.",
        "family_results_title": "Possible leads",
        "family_results_sub": (
            "These are rule-based clues from transaction descriptions and distinct months. "
            "They are not proof of ownership, an active product, a balance, a beneficiary or "
            "an asset. Confirm every lead with the institution."
        ),
        "leads_found": "possible leads found",
        "no_leads": (
            "No configured clue categories matched this statement. That does not mean there "
            "are no financial products; it only means the small keyword dictionary did not match."
        ),
        "evidence_title": "Exact transaction rows that caused the match",
        "rule_title": "Rule that detected this lead",
        "pattern_strength_label": "Pattern strength (rule-based heuristic only)",
        "strength_low": "Low — single clue",
        "strength_medium": "Medium pattern",
        "strength_strong": "Strong pattern",
        "what_not_prove": "What this does not prove",
        "next_step_label": "Suggested next step",
        "official_link_label": "Official source link",
        "not_searched_note": "We have not searched this portal; open it to verify the lead.",
        "lead_note": (
            "Lead only. A transaction alone does not prove ownership, coverage, a balance, "
            "units held, outstanding principal, a beneficiary or claim eligibility."
        ),
        "family_note_title": "Session-only case note",
        "family_note_help": (
            "Keep your own questions and next steps. This note is not saved and is cleared by "
            "Reset demo. Do not enter real account numbers, UPI IDs or other identifiers."
        ),
        "family_steps_title": "Your next steps",
        "family_steps_sub": "Session-only checklist. This does not verify any asset or authority.",
        "family_step_1": "Contact the institution using its official contact details",
        "family_step_2": "Open the relevant official portal and verify the lead",
        "family_step_3": "Keep written acknowledgements and records you control",
        "family_progress": "steps marked done",

        "sources_title": "Sources & limitations",
        "sources_sub": (
            "Official links are navigation only. The app does not query, scrape, automate or "
            "claim to have searched any portal."
        ),
        "no_portal_queried": (
            "No insurer, bank, UPI mandate, government or Sarvam portal was queried for this "
            "demo. No live financial data was retrieved."
        ),
        "limitations_title": "What this prototype cannot do",
        "limitations_body": (
            "It does not decide coverage, eligibility, claim approval or settlement; does not "
            "predict payout; does not determine legal heirs or authority; does not verify "
            "document authenticity; does not provide legal, medical, tax or investment advice; "
            "does not file claims, complaints or cancellations; and does not access another "
            "person's account. A death certificate alone is not presented as sufficient "
            "authority for every record or asset."
        ),
        "source_checked_label": "Link inventory date",
        "source_type_label": "Source type",
        "topic_documents": "Suggested claim documents",
        "topic_reimbursement_process": "Reimbursement process",
        "topic_waiting_period": "Waiting periods",
        "topic_exclusions": "Exclusions",
        "topic_grievance": "Grievance and escalation",
        "topic_claim_intimation": "Claim intimation",
        "topic_additional_documents": "Additional documents",
        "topic_payment_safety": "Payment safety",
        "category_insurance": "Possible insurance payment",
        "category_investment": "Possible investment or SIP",
        "category_lender": "Possible lender or EMI",
        "category_subscription": "Possible recurring subscription",
        "rule_single": (
            "Rule: the description contains the keyword “{keyword}”. Only one matching row was "
            "found, so this is a single clue, not a recurring pattern."
        ),
        "rule_same_month": (
            "Rule: the description contains the keyword “{keyword}”. {count} matching rows "
            "appear in the same month ({months}); this does not establish monthly recurrence."
        ),
        "rule_recurring": (
            "Rule: the description contains the keyword “{keyword}”, and matching rows appear "
            "in {month_count} distinct months ({months}). This is a rule-based pattern, not "
            "proof of ownership."
        ),
        "does_not_prove_insurance": (
            "It does not prove an active policy, coverage, a beneficiary, a premium due, a "
            "payout or that the institution holds any record for you."
        ),
        "does_not_prove_investment": (
            "It does not prove units held, current value, ownership, a folio, a nominee or that "
            "any amount is unclaimed."
        ),
        "does_not_prove_lender": (
            "It does not prove an outstanding loan, principal, interest, ownership or that the "
            "loan is still active."
        ),
        "does_not_prove_subscription": (
            "It does not prove an active subscription, a refund due, ownership or a cancellation "
            "right."
        ),
        "next_step_insurance": (
            "Contact the insurer named in the statement through its official website or written "
            "policy documents. Ask whether a policy exists and how to verify it. Do not share "
            "OTP, PIN or passwords."
        ),
        "next_step_investment": (
            "Contact the institution or registrar named in the statement. If relevant, open the "
            "official Common Landing Portal, RBI UDGAM or IEPFA/SEBI guidance yourself."
        ),
        "next_step_lender": (
            "Contact the lender using the official contact details on the statement or its "
            "official website. Ask for written confirmation; do not rely on links from strangers."
        ),
        "next_step_subscription": (
            "Contact the service provider through its official channel. Do not cancel or change "
            "a mandate from this prototype; it has no account access."
        ),
        "draft_missing_subject": "Draft follow-up: missing document categories for {case_id}",
        "draft_status_subject": "Draft request: status of fictional claim {case_id}",
        "draft_additional_subject": "Draft response: additional information for {case_id}",
        "draft_grievance_subject": "Draft grievance: fictional claim {case_id}",
        "draft_missing_body": (
            "Dear {insurer} Claims Team,\n\n"
            "I am writing about the fictional demo health reimbursement case {case_id} under "
            "{policy}.\n\n"
            "I have marked these document categories as provided: {marked}.\n"
            "These categories are still unmarked: {unmarked}.\n\n"
            "Could you please confirm your actual document requirements for this policy and the "
            "official channel for submitting them? Please provide a written acknowledgement or "
            "reference number through your official process.\n\n"
            "This is a draft prepared with a prototype. I will review and send it myself.\n\n"
            "Regards,\nDemo claimant (fictional)"
        ),
        "draft_status_body": (
            "Dear {insurer} Claims Team,\n\n"
            "I am writing about the fictional demo health reimbursement case {case_id} under "
            "{policy}.\n\n"
            "Could you please confirm the current status of this claim and whether you need any "
            "further document categories from me? Please reply through your official channel "
            "with any reference number and the date stated by your office.\n\n"
            "This is a draft prepared with a prototype. I will review and send it myself.\n\n"
            "Regards,\nDemo claimant (fictional)"
        ),
        "draft_additional_body": (
            "Dear {insurer} Claims Team,\n\n"
            "I am writing about the fictional demo health reimbursement case {case_id} under "
            "{policy}.\n\n"
            "Thank you for your request for more information. I understand that a request for "
            "additional documents is not a coverage or approval decision. I am reviewing the "
            "category you asked about: {category}.\n\n"
            "Could you please confirm the exact document you need and the official channel for "
            "sending it? Please provide a written acknowledgement.\n\n"
            "This is a draft prepared with a prototype. I will review and send it myself.\n\n"
            "Regards,\nDemo claimant (fictional)"
        ),
        "draft_grievance_body": (
            "Dear {insurer} Grievance Redressal Officer,\n\n"
            "I am writing about the fictional demo health reimbursement case {case_id} under "
            "{policy}.\n\n"
            "I would like to raise a grievance about the handling of this claim. The categories "
            "I have marked as provided are: {marked}. The categories still unmarked are: "
            "{unmarked}.\n\n"
            "Please provide a written acknowledgement and explain the next step through your "
            "official grievance process. I understand that this prototype does not decide "
            "eligibility or any deadline.\n\n"
            "This is a draft prepared with a prototype. I will review and send it myself.\n\n"
            "Regards,\nDemo claimant (fictional)"
        ),
    },
    "hi": {
        "app_title": "विरासत साथी",
        "app_tagline": "जब ज़रूरत हो तब वित्तीय मार्गदर्शन। जब सबसे अधिक सहारा चाहिए तब साथ।",
        "independent": "स्वतंत्र हैकाथॉन प्रोटोटाइप",
        "prototype_label": "स्वतंत्र हैकाथॉन प्रोटोटाइप · डेमो डेटा",
        "demo_data_label": "डेमो डेटा",
        "privacy_banner": (
            "हैकाथॉन प्रोटोटाइप — काल्पनिक डेमो केस का उपयोग करें। वास्तविक चिकित्सा, "
            "बीमा, बैंकिंग या मृत व्यक्ति के रिकॉर्ड अपलोड न करें।"
        ),
        "language_label": "भाषा",
        "reset_demo": "डेमो रीसेट करें",
        "reset_help": "यह सत्र साफ़ करता है और काल्पनिक डेमो केस पर लौटता है।",
        "home_heading": "आपको किस चीज़ में मदद चाहिए?",
        "home_sub": (
            "दो शांत, प्रमाण-पहले यात्राएँ। प्रोटोटाइप समझाता और तैयारी करता है; "
            "यह कवरेज, स्वामित्व या दावा स्वीकृति तय नहीं करता।"
        ),
        "claims_card_title": "दावा साथी",
        "claims_card_desc": (
            "बीमा दावा तैयार करने या फ़ॉलो-अप में मदद। क्लॉज़-संदर्भित डेमो पॉलिसी, "
            "चेकलिस्ट, ड्राफ़्ट और ट्रैकर के साथ काल्पनिक स्वास्थ्य प्रतिपूर्ति केस।"
        ),
        "claims_card_cta": "दावा साथी खोलें",
        "family_card_title": "परिवार वित्त खोजक",
        "family_card_desc": (
            "किसी नुकसान के बाद वित्तीय सुराग और अगले कदम खोजने में मदद। काल्पनिक "
            "स्टेटमेंट में संभावित बीमा, निवेश, ऋण या सदस्यता के संकेत देखें।"
        ),
        "family_card_cta": "परिवार वित्त खोजक खोलें",
        "home_trust_note": (
            "AI समझाता और सहायता करता है। नियम जाँचते हैं। आधिकारिक स्रोत आवश्यकताएँ "
            "स्थापित करते हैं। निर्णय उपयोगकर्ता लेता है।"
        ),
        "journey_01": "यात्रा 01 · दावा",
        "journey_02": "यात्रा 02 · परिवार",
        "back_home": "← होम पर लौटें",
        "footer_note": (
            "स्वतंत्र हैकाथॉन प्रोटोटाइप। Paytm, किसी बीमाकर्ता, IRDAI, RBI या Sarvam AI "
            "से संबद्ध नहीं। यह कानूनी राय या अनुपालन प्रमाणन नहीं है।"
        ),
        "footer_rule": "मॉडल समझाता है; नियम जाँचते हैं; संस्था निर्णय लेती है।",

        "claims_heading": "दावा साथी",
        "claims_sub": (
            "काल्पनिक स्वास्थ्य प्रतिपूर्ति दावा तैयार करें, हर मद के पीछे का स्रोत देखें, "
            "फ़ॉलो-अप ड्राफ़्ट बनाएँ और अपने अगले कदम रखें।"
        ),
        "demo_case_label": "डेमो केस",
        "load_demo_claim": "डेमो दावा लोड करें",
        "reload_demo": "डेमो दावा फिर लोड करें",
        "demo_loaded": "डेमो केस लोड हो गया",
        "claim_overview": "दावा अवलोकन",
        "product_label": "उत्पाद",
        "claim_type_label": "दावा प्रकार",
        "claim_type_value": "अस्पताल से छुट्टी के बाद प्रतिपूर्ति",
        "claim_state_label": "डेमो दावे की स्थिति",
        "claimant_label": "दावेदार",
        "hospital_label": "अस्पताल",
        "policy_label": "पॉलिसी",
        "checklist_source_label": "चेकलिस्ट स्रोत",
        "claims_disclaimer": (
            "यह ऐप पॉलिसी कवरेज, दावा स्वीकृति, भुगतान या पात्रता तय नहीं करता। यह "
            "जानकारी और तैयारी सहायक है, बीमाकर्ता, ब्रोकर, TPA, वकील, डॉक्टर या सर्वेयर नहीं।"
        ),
        "policy_facts_title": "पॉलिसी और दावे के तथ्य",
        "policy_facts_sub": (
            "नीचे का प्रत्येक कथन काल्पनिक डेमो पॉलिसी से है और क्लॉज़ आईडी व पृष्ठ देता है। "
            "शब्दावली सतर्क है: डेमो पॉलिसी का पाठ कहता है…, यह नहीं कि आप कवर हैं।"
        ),
        "policy_lookup_label": "डेमो पॉलिसी में विषय खोजें",
        "policy_lookup_help": (
            "यह प्रोटोटाइप केवल शामिल काल्पनिक फ़िक्सचर से उत्तर देता है। यह आपकी "
            "वास्तविक पॉलिसी सत्यापित नहीं कर सकता। विषय न होने पर यह स्पष्ट कहता है और "
            "बीमाकर्ता मार्ग लिंक करता है।"
        ),
        "choose_topic": "विषय चुनें",
        "policy_source_caption": "स्रोत: काल्पनिक डेमो पॉलिसी फ़िक्सचर",
        "clause_label": "क्लॉज़",
        "page_label": "पृष्ठ",
        "synthetic_sample_wording": "काल्पनिक नमूना पाठ — वास्तविक पॉलिसी नहीं।",
        "not_verified": "उपलब्ध जानकारी में सत्यापित नहीं है।",
        "insurer_link_cta": "आधिकारिक बीमाकर्ता/नियामक मार्ग खोलें",
        "checklist_title": "दस्तावेज़ चेकलिस्ट",
        "checklist_sub": (
            "ये श्रेणियाँ data/demo_claim.json से हैं। ये इस काल्पनिक केस के लिए उदाहरण हैं, "
            "हर बीमाकर्ता या उत्पाद के लिए सार्वभौमिक चेकलिस्ट नहीं।"
        ),
        "checklist_validation_note": (
            "किसी मद पर चिह्न लगाने का अर्थ केवल यह है कि आपने उसे प्रदान के रूप में "
            "चिह्नित किया। प्रोटोटाइप प्रामाणिकता, शुद्धता या पर्याप्तता सत्यापित नहीं करता, "
            "और यह संकेत नहीं देता कि बीमाकर्ता दस्तावेज़ या दावा स्वीकार करेगा।"
        ),
        "status_not_marked": "चिह्नित नहीं",
        "status_marked_provided": "प्रदान के रूप में चिह्नित",
        "status_needs_confirmation": "बीमाकर्ता से पुष्टि करनी है",
        "why_listed": "यह क्यों सूचीबद्ध है",
        "source_id_label": "स्रोत आईडी",
        "checklist_progress_marked": "प्रदान के रूप में चिह्नित",
        "checklist_progress_remaining": "अभी चिह्नित नहीं",
        "checklist_progress_confirm": "बीमाकर्ता से पुष्टि करनी है",
        "checklist_progress_caption": (
            "गिनती आपके चेकबॉक्स से नियतात्मक है। पूर्ण का अर्थ केवल चेकलिस्ट चिह्नित करना "
            "है; इसका अर्थ कभी दावा स्वीकृत या दस्तावेज़ पर्याप्त नहीं है।"
        ),
        "reset_checklist": "चेकलिस्ट चिह्न साफ़ करें",
        "draft_title": "उत्तर तैयार करने में मदद",
        "draft_sub": (
            "केवल काल्पनिक डेमो केस फ़ील्ड और चेकलिस्ट श्रेणी नामों से नियतात्मक ड्राफ़्ट "
            "बनाएँ। कॉपी या डाउनलोड से पहले उसे समीक्षा करें और संपादित करें।"
        ),
        "draft_kind_label": "ड्राफ़्ट प्रकार",
        "draft_missing_label": "अनुपस्थित दस्तावेज़ श्रेणी",
        "generate_draft": "ड्राफ़्ट बनाएँ",
        "draft_review_label": "मैंने यह ड्राफ़्ट समीक्षा किया है। मैं समझता हूँ कि यह ड्राफ़्ट है और मैं इसे स्वयं भेजूँगा।",
        "download_draft": "ड्राफ़्ट डाउनलोड करें (.txt)",
        "draft_no_submission": (
            "कोई ईमेल, WhatsApp, बीमाकर्ता API या पोर्टल सबमिशन लागू नहीं है। कुछ भी कहीं "
            "नहीं भेजा जाता। ड्राफ़्ट कॉपी या डाउनलोड करें और बीमाकर्ता के आधिकारिक चैनल से "
            "स्वयं भेजें।"
        ),
        "draft_demo_only": "डेमो ड्राफ़्ट — केवल काल्पनिक केस। उपयोग से पहले संपादित करें।",
        "draft_empty": "ड्राफ़्ट प्रकार चुनें और ड्राफ़्ट बनाएँ दबाएँ।",
        "draft_kind_missing": "अनुपस्थित दस्तावेज़ फ़ॉलो-अप",
        "draft_kind_status": "दावे की स्थिति पूछें",
        "draft_kind_additional": "अधिक जानकारी के अनुरोध का उत्तर",
        "draft_kind_grievance": "बीमाकर्ता शिकायत तैयार करें",
        "tracker_title": "अगले कदम ट्रैक करें",
        "tracker_sub": (
            "केवल सत्र का टाइमलाइन। अनुस्मारक तारीख केवल तब दर्ज करें जब बीमाकर्ता ने "
            "बताई हो। प्रोटोटाइप कानूनी या नियामक समय-सीमा निकालता या मानता नहीं है।"
        ),
        "due_date_label": "बीमाकर्ता द्वारा बताई अनुस्मारक तारीख (वैकल्पिक)",
        "due_date_help": "YYYY-MM-DD उपयोग करें। कोई तारीख न बताई गई हो तो खाली छोड़ें।",
        "notes_label": "नोट्स",
        "mark_done": "पूर्ण चिह्नित करें",
        "tracker_progress": "कदम पूर्ण चिह्नित",
        "escalation_title": "एस्केलेशन सहायता",
        "escalation_sub": (
            "केवल सरल भाषा के मार्ग। प्रोटोटाइप शिकायत दर्ज नहीं करता, पात्रता तय नहीं "
            "करता और असत्यापित समय-सीमा नहीं जोड़ता।"
        ),
        "escalation_step_1": (
            "पहले बीमाकर्ता के आधिकारिक चैनल से बीमाकर्ता के शिकायत निवारण अधिकारी से "
            "संपर्क करें। लिखित पावती रखें।"
        ),
        "escalation_step_2": (
            "यदि मामला अनसुलझा रहे या उत्तर संतोषजनक न हो, तो आधिकारिक स्रोत पर बीमा भरोसा "
            "की वर्तमान प्रक्रिया जाँचें।"
        ),
        "escalation_step_3": (
            "Council for Insurance Ombudsmen स्रोत पर वर्तमान लोकपाल पात्रता और प्रक्रिया "
            "जाँचें। आवश्यकताएँ बदल सकती हैं; यहाँ कुछ भी कानूनी निष्कर्ष नहीं है।"
        ),
        "escalation_links_title": "आधिकारिक एस्केलेशन लिंक",
        "anti_fraud_title": "भुगतान और धोखाधड़ी चेतावनी",
        "anti_fraud_warning": (
            "दावे की राशि पाने के लिए कभी शुल्क न दें। किसी अजनबी द्वारा भेजा गया QR कोड "
            "स्कैन न करें। OTP, UPI पिन, पासवर्ड या कार्ड पिन कभी साझा न करें। IRDAI/बीमा "
            "भरोसा शिकायत हल करने के लिए शिकायतकर्ताओं से भुगतान नहीं माँगता।"
        ),
        "case_summary_title": "डेमो केस सारांश डाउनलोड करें",
        "case_summary_sub": (
            "DEMO वॉटरमार्क वाला स्थानीय, मेमोरी-आधारित टेक्स्ट सारांश। यह बीमाकर्ता का "
            "निर्णय, कानूनी सलाह या कवरेज का प्रमाण नहीं है।"
        ),
        "download_case_summary": "डेमो सारांश डाउनलोड करें (.txt)",
        "local_doc_title": "स्थानीय दस्तावेज़ पठनीयता जाँच (वैकल्पिक)",
        "local_doc_sub": (
            "वैकल्पिक, केवल-स्थानीय PDF/TXT पठनीयता सहायता। यह प्रामाणिकता, पर्याप्तता, "
            "कवरेज या दावा पात्रता सत्यापित नहीं करता, और कभी Sarvam को नहीं भेजा जाता।"
        ),
        "upload_ack_label": (
            "मैं समझता हूँ कि यह प्रोटोटाइप केवल काल्पनिक डेमो डेटा के लिए है। यदि मैं "
            "स्थानीय फ़ाइल चुनता हूँ, तो वह मेमोरी में रहती है, कभी Sarvam को नहीं भेजी जाती, "
            "और मैं वास्तविक चिकित्सा, बीमा या बैंकिंग रिकॉर्ड अपलोड नहीं करूँगा।"
        ),
        "upload_doc": "स्थानीय PDF या TXT फ़ाइल चुनें",
        "upload_doc_help": "केवल PDF, TXT · अधिकतम 10 MB · मेमोरी में प्रोसेस · सहेजा नहीं जाता",
        "pdf_ocr_note": "OCR समर्थित नहीं है। स्कैन/केवल-छवि PDF यहाँ पढ़े नहीं जा सकते।",
        "pdf_readable": "चयनित टेक्स्ट मिला",
        "pdf_not_readable": "पठनीय टेक्स्ट नहीं मिला",
        "uploaded_doc_ai_disabled": "इस प्रोटोटाइप में उपयोगकर्ता-दस्तावेज़ों के लिए AI बंद है।",
        "sarvam_switch_label": "केवल काल्पनिक डेमो सामग्री के लिए Sarvam AI का उपयोग करें",
        "sarvam_switch_help": (
            "वैकल्पिक। डेमो इसके बिना पूरी तरह काम करता है। AI आपका मुक्त टेक्स्ट, "
            "अपलोड की गई फ़ाइलें या लेन-देन पंक्तियाँ कभी नहीं देखता।"
        ),
        "sarvam_ai_note": (
            "काल्पनिक डेमो सामग्री की AI-जनित व्याख्या। सभी आवश्यकताओं को अपने बीमाकर्ता "
            "से सत्यापित करें।"
        ),
        "sarvam_disabled_note": (
            "नियतात्मक व्याख्या। Sarvam कॉन्फ़िगर नहीं है या बंद है।"
        ),
        "sarvam_fallback_note": (
            "Sarvam उपलब्ध नहीं था या अनुपयोगी टेक्स्ट लौटाया, इसलिए यह नियतात्मक "
            "व्याख्या दिखाई जा रही है।"
        ),
        "sarvam_source_label": "स्थिर काल्पनिक स्रोत अंश",
        "sarvam_verify_note": (
            "मूल चेकलिस्ट इस डेमो के लिए दिखाई देती और प्रामाणिक रहती है। AI प्रतिलिपि "
            "कभी आवश्यकता, समय-सीमा या पात्रता निर्णय नहीं बनाती।"
        ),
        "sarvam_status_label": "Sarvam स्थिति",
        "sarvam_status_disabled": "बंद — नियतात्मक मोड",
        "sarvam_status_no_key": "बंद — कोई API कुंजी कॉन्फ़िगर नहीं",
        "sarvam_status_deprecated_model": "बंद — पुराना मॉडल आईडी कॉन्फ़िगर है",
        "sarvam_status_bad_url": "बंद — बेस URL को https होना चाहिए",
        "sarvam_status_ready": "कॉन्फ़िगर — वैकल्पिक काल्पनिक-सामग्री मोड",
        "fallback_claim_form": (
            "डेमो चेकलिस्ट में भरा हुआ दावा फ़ॉर्म सूचीबद्ध है। इसे प्रदान के रूप में "
            "चिह्नित करना केवल आपका नोट दर्ज करता है; यह फ़ॉर्म को सत्यापित नहीं करता। "
            "बीमाकर्ता से वास्तविक आवश्यकता की पुष्टि करें।"
        ),
        "fallback_discharge_summary": (
            "डेमो चेकलिस्ट में अस्पताल की डिस्चार्ज समरी सूचीबद्ध है। इसे प्रदान के रूप "
            "में चिह्नित करना केवल आपका नोट दर्ज करता है; यह दस्तावेज़ सत्यापित नहीं करता "
            "और बीमाकर्ता स्वीकृति का संकेत नहीं देता। वास्तविक आवश्यकता की पुष्टि करें।"
        ),
        "fallback_itemised_bill": (
            "डेमो चेकलिस्ट में अस्पताल का आइटम-वार अंतिम बिल सूचीबद्ध है। इसे प्रदान के "
            "रूप में चिह्नित करना केवल आपका नोट दर्ज करता है। प्रोटोटाइप बिल की जाँच या "
            "यह तय नहीं करता कि कोई राशि देय है।"
        ),
        "fallback_payment_receipt": (
            "डेमो चेकलिस्ट में भुगतान रसीदें सूचीबद्ध हैं। इन्हें प्रदान के रूप में "
            "चिह्नित करना केवल आपका नोट दर्ज करता है। बीमाकर्ता से पुष्टि करें कि वह कौन "
            "सी रसीदें और किस रूप में चाहता है।"
        ),
        "fallback_policy_schedule": (
            "डेमो चेकलिस्ट में पॉलिसी शेड्यूल सूचीबद्ध है। इसे प्रदान के रूप में चिह्नित "
            "करना केवल आपका नोट दर्ज करता है। प्रोटोटाइप शेड्यूल सत्यापित या कवरेज तय "
            "नहीं करता।"
        ),
        "fallback_supporting_reports": (
            "डेमो पॉलिसी कहती है कि बीमाकर्ता जहाँ लागू हो प्रिस्क्रिप्शन या जाँच रिपोर्ट "
            "माँग सकता है। पुष्टि करें कि बीमाकर्ता इस दावे के लिए उन्हें चाहता है या नहीं; "
            "यह प्रोटोटाइप चिकित्सा आवश्यकता तय नहीं करता।"
        ),
        "sarvam_request_button": "AI व्याख्या प्राप्त करें",
        "sarvam_choose_category": "AI व्याख्या के लिए चेकलिस्ट श्रेणी",
        "sarvam_not_requested": (
            "नियतात्मक व्याख्या दिखाई गई है। काल्पनिक स्रोत अंश की वैकल्पिक AI व्याख्या "
            "का अनुरोध करने के लिए बटन का उपयोग करें।"
        ),
        "due_date_invalid": "YYYY-MM-DD उपयोग करें, या अनुस्मारक खाली छोड़ें।",
        "no_official_link": (
            "इस सुराग के लिए कोई आधिकारिक पोर्टल लिंक नहीं है। संस्था के आधिकारिक संपर्क "
            "विवरण से पुष्टि करें।"
        ),
        "family_no_ai_note": (
            "परिवार वित्त खोजक केवल नियतात्मक मिलान का उपयोग करता है। लेन-देन पंक्तियों "
            "के लिए कोई AI मॉडल नहीं बुलाया जाता।"
        ),
        "local_upload_label": "स्थानीय अपलोड — केवल काल्पनिक डेटा",
        "statement_rows_title": "मिलान में उपयोग हुई स्टेटमेंट पंक्तियाँ",
        "uploaded_file_processed": "फ़ाइल स्थानीय रूप से मेमोरी में प्रोसेस हुई। कुछ सहेजा नहीं गया।",
        "statement_rows_metric": "स्टेटमेंट पंक्तियाँ",
        "recurring_patterns_metric": "आवर्ती पैटर्न",
        "choose_csv": (
            "संभावित सुराग देखने के लिए ऊपर CSV फ़ाइल चुनें। फ़ाइल स्थानीय रूप से मेमोरी में "
            "प्रोसेस होती है और कभी Sarvam को नहीं भेजी जाती।"
        ),
        "table_row": "पंक्ति",
        "table_date": "तारीख",
        "table_description": "विवरण",
        "table_amount": "राशि",
        "table_direction": "दिशा",
        "page_word": "पृष्ठ",
        "row_word": "पंक्ति",
        "ai_generated_label": "AI-जनित",
        "footer_license": "MIT-लाइसेंस प्रोटोटाइप कोड · केवल काल्पनिक फ़िक्सचर।",
        "fixture_error": "काल्पनिक डेमो फ़िक्सचर सत्यापन में विफल रहा",

        "family_heading": "परिवार वित्त खोजक",
        "family_sub": (
            "काल्पनिक लेन-देन स्टेटमेंट पढ़ें, संभावित वित्तीय सुराग खोजें, और हर मिलान "
            "के पीछे की सटीक पंक्तियाँ देखें। हर परिणाम सुराग है, प्रमाण नहीं।"
        ),
        "synthetic_data_label": "काल्पनिक डेटा",
        "load_synthetic": "काल्पनिक स्टेटमेंट लोड करें",
        "statement_mode_label": "स्टेटमेंट स्रोत",
        "mode_demo": "शामिल काल्पनिक स्टेटमेंट",
        "mode_upload": "CSV अपलोड करें (केवल स्थानीय)",
        "upload_csv_label": "स्थानीय CSV स्टेटमेंट चुनें",
        "upload_csv_help": "केवल CSV · अधिकतम 10 MB · मेमोरी में प्रोसेस · सहेजा नहीं जाता",
        "upload_local_note": (
            "CSV स्थानीय रूप से मेमोरी में पार्स होता है। पंक्तियाँ कभी डिस्क पर लिखी, लॉग "
            "या Sarvam या किसी बाहरी सेवा को नहीं भेजी जाती।"
        ),
        "ai_disabled_upload": "इस प्रोटोटाइप में उपयोगकर्ता-रिकॉर्ड के लिए AI बंद है।",
        "family_results_title": "संभावित सुराग",
        "family_results_sub": (
            "ये लेन-देन विवरण और अलग-अलग महीनों पर आधारित नियम-आधारित सुराग हैं। ये "
            "स्वामित्व, सक्रिय उत्पाद, शेष राशि, लाभार्थी या संपत्ति का प्रमाण नहीं। हर "
            "सुराग की पुष्टि संस्था से करें।"
        ),
        "leads_found": "संभावित सुराग मिले",
        "no_leads": (
            "इस स्टेटमेंट में कोई कॉन्फ़िगर श्रेणी नहीं मिली। इसका अर्थ यह नहीं कि कोई "
            "वित्तीय उत्पाद नहीं है; केवल यह कि छोटे कीवर्ड शब्दकोश से मिलान नहीं हुआ।"
        ),
        "evidence_title": "मिलान करने वाली सटीक लेन-देन पंक्तियाँ",
        "rule_title": "इस सुराग को पहचानने वाला नियम",
        "pattern_strength_label": "पैटर्न की मज़बूती (केवल नियम-आधारित अनुमान)",
        "strength_low": "कम — एकल सुराग",
        "strength_medium": "मध्यम पैटर्न",
        "strength_strong": "मज़बूत पैटर्न",
        "what_not_prove": "यह क्या सिद्ध नहीं करता",
        "next_step_label": "सुझाया गया अगला कदम",
        "official_link_label": "आधिकारिक स्रोत लिंक",
        "not_searched_note": "हमने यह पोर्टल नहीं खोजा; सुराग सत्यापित करने के लिए इसे खोलें।",
        "lead_note": (
            "केवल सुराग। अकेला लेन-देन स्वामित्व, कवरेज, शेष राशि, इकाइयाँ, बकाया "
            "मूलधन, लाभार्थी या दावा पात्रता सिद्ध नहीं करता।"
        ),
        "family_note_title": "केवल-सत्र केस नोट",
        "family_note_help": (
            "अपने प्रश्न और अगले कदम रखें। यह नोट सहेजा नहीं जाता और डेमो रीसेट से साफ़ "
            "होता है। वास्तविक खाता संख्या, UPI आईडी या अन्य पहचानकर्ता दर्ज न करें।"
        ),
        "family_steps_title": "आपके अगले कदम",
        "family_steps_sub": "केवल-सत्र चेकलिस्ट। यह किसी संपत्ति या अधिकार को सत्यापित नहीं करता।",
        "family_step_1": "संस्था के आधिकारिक संपर्क विवरण से संपर्क करें",
        "family_step_2": "संबंधित आधिकारिक पोर्टल खोलें और सुराग सत्यापित करें",
        "family_step_3": "लिखित पावतियाँ और अपने नियंत्रण के रिकॉर्ड रखें",
        "family_progress": "कदम पूर्ण चिह्नित",

        "sources_title": "स्रोत और सीमाएँ",
        "sources_sub": (
            "आधिकारिक लिंक केवल नेविगेशन हैं। ऐप किसी पोर्टल को क्वेरी, स्क्रैप या "
            "स्वचालित नहीं करता और यह दावा नहीं करता कि उसने कोई पोर्टल खोजा है।"
        ),
        "no_portal_queried": (
            "इस डेमो के लिए किसी बीमाकर्ता, बैंक, UPI मैंडेट, सरकारी या Sarvam पोर्टल को "
            "क्वेरी नहीं किया गया। कोई लाइव वित्तीय डेटा नहीं लिया गया।"
        ),
        "limitations_title": "यह प्रोटोटाइप क्या नहीं कर सकता",
        "limitations_body": (
            "यह कवरेज, पात्रता, दावा स्वीकृति या निपटान तय नहीं करता; भुगतान का अनुमान "
            "नहीं लगाता; कानूनी उत्तराधिकारी या अधिकार तय नहीं करता; दस्तावेज़ प्रामाणिकता "
            "सत्यापित नहीं करता; कानूनी, चिकित्सा, कर या निवेश सलाह नहीं देता; दावे, "
            "शिकायतें या रद्दीकरण दर्ज नहीं करता; और किसी अन्य व्यक्ति के खाते तक पहुँच नहीं "
            "करता। केवल मृत्यु प्रमाणपत्र को हर रिकॉर्ड या संपत्ति के लिए पर्याप्त अधिकार "
            "नहीं बताया जाता।"
        ),
        "source_checked_label": "लिंक सूची तिथि",
        "source_type_label": "स्रोत प्रकार",
        "topic_documents": "सुझाए गए दावा दस्तावेज़",
        "topic_reimbursement_process": "प्रतिपूर्ति प्रक्रिया",
        "topic_waiting_period": "प्रतीक्षा अवधि",
        "topic_exclusions": "अपवर्जन",
        "topic_grievance": "शिकायत और एस्केलेशन",
        "topic_claim_intimation": "दावा सूचना",
        "topic_additional_documents": "अतिरिक्त दस्तावेज़",
        "topic_payment_safety": "भुगतान सुरक्षा",
        "category_insurance": "संभावित बीमा भुगतान",
        "category_investment": "संभावित निवेश या SIP",
        "category_lender": "संभावित ऋणदाता या EMI",
        "category_subscription": "संभावित आवर्ती सदस्यता",
        "rule_single": (
            "नियम: विवरण में “{keyword}” कीवर्ड है। केवल एक मिलान पंक्ति मिली, इसलिए यह "
            "एकल सुराग है, आवर्ती पैटर्न नहीं।"
        ),
        "rule_same_month": (
            "नियम: विवरण में “{keyword}” कीवर्ड है। {count} मिलान पंक्तियाँ एक ही महीने "
            "({months}) में हैं; यह मासिक पुनरावृत्ति सिद्ध नहीं करता।"
        ),
        "rule_recurring": (
            "नियम: विवरण में “{keyword}” कीवर्ड है और मिलान पंक्तियाँ {month_count} अलग "
            "महीनों ({months}) में हैं। यह नियम-आधारित पैटर्न है, स्वामित्व का प्रमाण नहीं।"
        ),
        "does_not_prove_insurance": (
            "यह सक्रिय पॉलिसी, कवरेज, लाभार्थी, देय प्रीमियम, भुगतान या यह सिद्ध नहीं करता "
            "कि संस्था के पास आपका कोई रिकॉर्ड है।"
        ),
        "does_not_prove_investment": (
            "यह धारित इकाइयाँ, वर्तमान मूल्य, स्वामित्व, फ़ोलियो, नामांकित व्यक्ति या यह "
            "सिद्ध नहीं करता कि कोई राशि दावा-रहित है।"
        ),
        "does_not_prove_lender": (
            "यह बकाया ऋण, मूलधन, ब्याज, स्वामित्व या यह सिद्ध नहीं करता कि ऋण अभी सक्रिय है।"
        ),
        "does_not_prove_subscription": (
            "यह सक्रिय सदस्यता, देय रिफ़ंड, स्वामित्व या रद्दीकरण अधिकार सिद्ध नहीं करता।"
        ),
        "next_step_insurance": (
            "स्टेटमेंट में नामित बीमाकर्ता से उसकी आधिकारिक वेबसाइट या लिखित पॉलिसी "
            "दस्तावेज़ों से संपर्क करें। पूछें कि क्या पॉलिसी है और उसे कैसे सत्यापित करें। "
            "OTP, पिन या पासवर्ड साझा न करें।"
        ),
        "next_step_investment": (
            "स्टेटमेंट में नामित संस्था या रजिस्ट्रार से संपर्क करें। यदि लागू हो, तो "
            "आधिकारिक Common Landing Portal, RBI UDGAM या IEPFA/SEBI मार्गदर्शन स्वयं खोलें।"
        ),
        "next_step_lender": (
            "स्टेटमेंट के आधिकारिक संपर्क विवरण या ऋणदाता की आधिकारिक वेबसाइट से संपर्क "
            "करें। लिखित पुष्टि माँगें; अजनबियों के लिंक पर भरोसा न करें।"
        ),
        "next_step_subscription": (
            "सेवा प्रदाता के आधिकारिक चैनल से संपर्क करें। इस प्रोटोटाइप से मैंडेट रद्द या "
            "बदलें नहीं; इसके पास खाता पहुँच नहीं है।"
        ),
        "draft_missing_subject": "ड्राफ़्ट फ़ॉलो-अप: {case_id} के लिए अनुपस्थित दस्तावेज़ श्रेणियाँ",
        "draft_status_subject": "ड्राफ़्ट अनुरोध: काल्पनिक दावा {case_id} की स्थिति",
        "draft_additional_subject": "ड्राफ़्ट उत्तर: {case_id} के लिए अतिरिक्त जानकारी",
        "draft_grievance_subject": "ड्राफ़्ट शिकायत: काल्पनिक दावा {case_id}",
        "draft_missing_body": (
            "प्रति: {insurer} दावा टीम,\n\n"
            "मैं {policy} के अंतर्गत काल्पनिक डेमो स्वास्थ्य प्रतिपूर्ति केस {case_id} के "
            "बारे में लिख रहा हूँ।\n\n"
            "मैंने इन दस्तावेज़ श्रेणियों को प्रदान के रूप में चिह्नित किया है: {marked}।\n"
            "ये श्रेणियाँ अभी चिह्नित नहीं हैं: {unmarked}।\n\n"
            "कृपया इस पॉलिसी के लिए अपनी वास्तविक दस्तावेज़ आवश्यकताएँ और जमा करने का "
            "आधिकारिक चैनल पुष्टि करें। कृपया अपनी आधिकारिक प्रक्रिया से लिखित पावती या "
            "संदर्भ संख्या दें।\n\n"
            "यह प्रोटोटाइप से तैयार ड्राफ़्ट है। मैं इसे समीक्षा कर स्वयं भेजूँगा।\n\n"
            "सादर,\nडेमो दावेदार (काल्पनिक)"
        ),
        "draft_status_body": (
            "प्रति: {insurer} दावा टीम,\n\n"
            "मैं {policy} के अंतर्गत काल्पनिक डेमो स्वास्थ्य प्रतिपूर्ति केस {case_id} के "
            "बारे में लिख रहा हूँ।\n\n"
            "कृपया इस दावे की वर्तमान स्थिति और क्या आपको मुझसे कोई और दस्तावेज़ श्रेणी "
            "चाहिए, इसकी पुष्टि करें। कृपया अपने आधिकारिक चैनल से संदर्भ संख्या और अपने "
            "कार्यालय द्वारा बताई तारीख के साथ उत्तर दें।\n\n"
            "यह प्रोटोटाइप से तैयार ड्राफ़्ट है। मैं इसे समीक्षा कर स्वयं भेजूँगा।\n\n"
            "सादर,\nडेमो दावेदार (काल्पनिक)"
        ),
        "draft_additional_body": (
            "प्रति: {insurer} दावा टीम,\n\n"
            "मैं {policy} के अंतर्गत काल्पनिक डेमो स्वास्थ्य प्रतिपूर्ति केस {case_id} के "
            "बारे में लिख रहा हूँ।\n\n"
            "अधिक जानकारी के आपके अनुरोध के लिए धन्यवाद। मैं समझता हूँ कि अतिरिक्त "
            "दस्तावेज़ों का अनुरोध कवरेज या स्वीकृति का निर्णय नहीं है। मैं उस श्रेणी की "
            "समीक्षा कर रहा हूँ जिसके बारे में आपने पूछा: {category}।\n\n"
            "कृपया ठीक वह दस्तावेज़ और भेजने का आधिकारिक चैनल पुष्टि करें। कृपया लिखित "
            "पावती दें।\n\n"
            "यह प्रोटोटाइप से तैयार ड्राफ़्ट है। मैं इसे समीक्षा कर स्वयं भेजूँगा।\n\n"
            "सादर,\nडेमो दावेदार (काल्पनिक)"
        ),
        "draft_grievance_body": (
            "प्रति: {insurer} शिकायत निवारण अधिकारी,\n\n"
            "मैं {policy} के अंतर्गत काल्पनिक डेमो स्वास्थ्य प्रतिपूर्ति केस {case_id} के "
            "बारे में लिख रहा हूँ।\n\n"
            "मैं इस दावे के संचालन के बारे में शिकायत दर्ज करना चाहता हूँ। जिन श्रेणियों "
            "को मैंने प्रदान के रूप में चिह्नित किया है: {marked}। जो श्रेणियाँ अभी चिह्नित "
            "नहीं हैं: {unmarked}।\n\n"
            "कृपया लिखित पावती दें और अपनी आधिकारिक शिकायत प्रक्रिया से अगला कदम बताएँ। "
            "मैं समझता हूँ कि यह प्रोटोटाइप पात्रता या किसी समय-सीमा का निर्णय नहीं करता।\n\n"
            "यह प्रोटोटाइप से तैयार ड्राफ़्ट है। मैं इसे समीक्षा कर स्वयं भेजूँगा।\n\n"
            "सादर,\nडेमो दावेदार (काल्पनिक)"
        ),
    },
}


def t(key: str, language: Language = "en") -> str:
    """Return a static string, falling back to English for an unknown key."""
    selected = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    if key in selected:
        return selected[key]
    return TRANSLATIONS["en"].get(key, key)


def topic_label(topic: str, language: Language = "en") -> str:
    return t(f"topic_{topic}", language)
