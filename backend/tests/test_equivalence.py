import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validators.logic import boolean_equivalence_check


def test_and_is_equivalent():
    result = boolean_equivalence_check(
        source_code="I0.0 AND I0.1 -> Q0.0",
        source_vendor="Siemens",
        target_code="XIC(I0.0) XIC(I0.1) OTE(Q0.0)",
        target_vendor="Rockwell",
    )
    assert result["status"] == "PASS"
    assert result["rows_tested"] == 4  # 2 inputs -> 2^2 rows
    assert result["rows_passed"] == 4


def test_or_is_equivalent():
    result = boolean_equivalence_check(
        source_code="I0.0 OR I0.1 -> Q0.0",
        source_vendor="Siemens",
        target_code="XIC(I0.0) OTE(Q0.0)\nXIC(I0.1) OTE(Q0.0)",
        target_vendor="Rockwell",
    )
    assert result["status"] == "PASS"


def test_incorrect_conversion_fails():
    # Deliberately wrong: AND source converted as if it were OR.
    result = boolean_equivalence_check(
        source_code="I0.0 AND I0.1 -> Q0.0",
        source_vendor="Siemens",
        target_code="XIC(I0.0) OTE(Q0.0)\nXIC(I0.1) OTE(Q0.0)",
        target_vendor="Rockwell",
    )
    assert result["status"] == "FAIL"
    assert result["rows_passed"] < result["rows_tested"]
