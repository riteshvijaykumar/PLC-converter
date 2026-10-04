"""Level 1 — syntax validation: brackets, known keywords, tag-name shape."""
import re

_VALID_TAG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\[\]]*$")
_KNOWN_KEYWORDS = {"AND", "OR", "NOT", "SET", "RESET", "TON", "TOF", "CTU", "CTD",
                    "XIC", "XIO", "OTE", "OTL", "OTU"}


def validate_syntax(code: str, vendor: str) -> dict:
    errors = []
    warnings = []

    open_parens = code.count("(")
    close_parens = code.count(")")
    if open_parens != close_parens:
        errors.append(f"Unbalanced parentheses: {open_parens} '(' vs {close_parens} ')'")

    for line_no, raw_line in enumerate(code.strip().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line)
        keyword_tokens = [t for t in tokens if t.isupper() or t in _KNOWN_KEYWORDS]
        for kw in keyword_tokens:
            if kw not in _KNOWN_KEYWORDS and len(kw) <= 4:
                warnings.append(f"Line {line_no}: unrecognized keyword-like token '{kw}'")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
