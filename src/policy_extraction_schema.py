"""The JSON schema sent to Sarvam Document AI Extract.

Every field description tells the model to preserve printed wording or return
nothing. The application never fills a missing value by inference.
"""

from __future__ import annotations

import json
from typing import Any

POLICY_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "description": (
                "Document type; identify whether this is an insurance policy document"
            ),
        },
        "insurer_name": {
            "type": "string",
            "description": "Name of the insurance company, as printed",
        },
        "product_name": {
            "type": "string",
            "description": "Insurance product or plan name, as printed",
        },
        "policyholder_name": {
            "type": "string",
            "description": "Name of policyholder, as printed",
        },
        "insured_persons": {
            "type": "string",
            "description": "Names of insured persons, if explicitly printed",
        },
        "policy_number": {
            "type": "string",
            "description": "Policy number, preserve exact characters",
        },
        "uin": {
            "type": "string",
            "description": "Insurance product UIN, if printed",
        },
        "policy_start_date": {
            "type": "string",
            "description": "Policy start date exactly as printed",
        },
        "policy_end_date": {
            "type": "string",
            "description": "Policy end date exactly as printed",
        },
        "sum_insured": {
            "type": "string",
            "description": (
                "Sum insured / coverage amount exactly as printed, including currency"
            ),
        },
        "premium_amount": {
            "type": "string",
            "description": "Premium amount exactly as printed, including currency",
        },
        "premium_frequency": {
            "type": "string",
            "description": "Payment frequency, only if printed",
        },
        "nominee_name": {
            "type": "string",
            "description": "Nominee name, if printed",
        },
        "nominee_relationship": {
            "type": "string",
            "description": "Nominee relationship, if printed",
        },
    },
}


def extraction_schema_json() -> str:
    return json.dumps(POLICY_EXTRACTION_SCHEMA, ensure_ascii=False)


__all__ = ["POLICY_EXTRACTION_SCHEMA", "extraction_schema_json"]
