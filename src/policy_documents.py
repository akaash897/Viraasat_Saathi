"""Render a policy document from session data without writing files.

Seeded policies do not ship with PDFs. The viewer therefore builds a small,
valid PDF in memory from the policy record so every policy has a document tab.
Uploaded external documents are stored separately in session state and shown
from those bytes when available.

The generated document is a prototype rendering, not an insurer-issued policy.
It deliberately uses the masked policy number only.
"""

from __future__ import annotations

import textwrap
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.insurance_inventory import (
    display_date,
    display_value,
    source_label,
    verification_label,
)

_PAGE_WIDTH = 595
_PAGE_HEIGHT = 842
_LEFT = 54
_TOP = 792


def _pdf_safe(value: object) -> str:
    text = str(value)
    replacements = {
        "₹": "Rs ",
        "–": "-",
        "—": "-",
        "•": "*",
        "…": "...",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _escape(value: object) -> str:
    return _pdf_safe(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_command(text: str, *, x: int, y: int, size: int, bold: bool) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf {x} {y} Td ({_escape(text)}) Tj ET"


def _build_pdf(lines: Sequence[tuple[str, int, bool]]) -> bytes:
    commands: list[str] = []
    y = _TOP
    for text, size, bold in lines:
        for wrapped in textwrap.wrap(
            _pdf_safe(text), width=92 if size <= 10 else 64
        ) or [""]:
            if y < 52:
                break
            commands.append(
                _text_command(wrapped, x=_LEFT, y=y, size=size, bold=bold)
            )
            y -= size + 6
        y -= 6
    content = "\n".join(commands).encode("cp1252", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
            b"/Contents 6 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def generate_policy_document(record: Mapping[str, Any]) -> bytes:
    """Build a one-page PDF from a normalised policy record."""
    period = (
        f"{display_date(record.get('policy_start_date'))} - "
        f"{display_date(record.get('policy_end_date'))}"
    )
    insured = ", ".join(str(item) for item in (record.get("insured_persons") or []))
    fields: list[tuple[str, object]] = [
        ("Insurer", display_value(record.get("insurer_name"))),
        ("Product / plan", display_value(record.get("product_name"))),
        ("Policyholder", display_value(record.get("policyholder_name"))),
        ("Insured persons", display_value(insured)),
        ("Policy number (masked)", display_value(record.get("policy_number_masked"))),
        ("UIN", display_value(record.get("uin"))),
        ("Policy period", period),
        ("Sum insured / coverage", display_value(record.get("sum_insured"))),
        ("Premium", display_value(record.get("premium_amount"))),
        ("Premium frequency", display_value(record.get("premium_frequency"))),
        ("Document source", source_label(record.get("source_type"))),
        ("Verification", verification_label(record.get("verification_status"))),
    ]

    lines: list[tuple[str, int, bool]] = [
        ("Virasat Saathi", 18, True),
        ("Policy document", 14, True),
        ("", 8, False),
    ]
    for label, value in fields:
        lines.append((f"{label}: {display_value(value)}", 10, False))
    lines.extend(
        [
            ("", 8, False),
            (
                "This document is a prototype rendering of session data. "
                "It is not issued by the insurer and does not confirm that "
                "cover is active.",
                9,
                False,
            ),
            (
                "Verify every detail with the insurer before relying on it.",
                9,
                False,
            ),
            (f"Generated on: {date.today().isoformat()}", 9, False),
        ]
    )
    return _build_pdf(lines)


def document_filename(record: Mapping[str, Any]) -> str:
    policy_id = str(record.get("policy_id") or "policy")
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in policy_id)
    return f"{safe or 'policy'}-document.pdf"


def is_pdf(data: bytes) -> bool:
    return bytes(data[:5]) == b"%PDF-"


__all__ = [
    "document_filename",
    "generate_policy_document",
    "is_pdf",
]
