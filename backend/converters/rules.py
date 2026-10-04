"""
Rule-based instruction mapping table (Module 4 in the project spec).

This is the "known instruction -> known instruction" fast path. Anything
whose IR type is NOT in these tables falls through to the AI engine stub
(ai/inference.py) for a best-effort suggestion, and is flagged with a
lower confidence score.
"""

SIEMENS_TO_AB_TYPES = {
    "AND": "XIC/XIC/OTE",
    "OR": "XIC/XIC/OTE (parallel branch)",
    "NOT": "XIO/OTE",
    "SET": "OTL",
    "RESET": "OTU",
    "TON": "TON",
    "TOF": "TOF",
    "CTU": "CTU",
    "CTD": "CTD",
}

AB_TO_SIEMENS_TYPES = {
    "AND": "AND",
    "OR": "OR",
    "NOT": "NOT",
    "SET": "SET (S)",
    "RESET": "RESET (R)",
    "TON": "TON",
    "TOF": "TOF",
    "CTU": "CTU",
    "CTD": "CTD",
}

SUPPORTED_TYPES = set(SIEMENS_TO_AB_TYPES.keys())
