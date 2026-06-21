"""Static violation -> Motor Vehicles Act (1988) mapping. Correct, instant, free.

This is the source of truth for legal grounding. The optional RAG bonus (free-form
Q&A over the Act) layers on top and must never sit on the verdict's critical path.
Verify exact sections/fines against your state's current notification before issuing.
"""

from __future__ import annotations

_ACT = "Motor Vehicles Act, 1988"

LEGAL_TABLE: dict[str, dict[str, str]] = {
    "HELMET_NON_COMPLIANCE": {"act": _ACT, "section": "194D", "fine": "₹1000"},
    "TRIPLE_RIDING": {"act": _ACT, "section": "128 / 194C", "fine": "₹1000"},
    "SEATBELT_NON_COMPLIANCE": {"act": _ACT, "section": "194B", "fine": "₹1000"},
    "STOP_LINE_VIOLATION": {"act": _ACT, "section": "177", "fine": "₹500"},
    "RED_LIGHT_VIOLATION": {"act": _ACT, "section": "184", "fine": "₹1000-5000"},
    "ILLEGAL_PARKING": {"act": _ACT, "section": "122 / 177", "fine": "₹500"},
    "WRONG_SIDE_DRIVING": {"act": _ACT, "section": "184", "fine": "₹1000-5000"},
}


def lookup(violation_type: str) -> dict[str, str] | None:
    return LEGAL_TABLE.get(violation_type)
