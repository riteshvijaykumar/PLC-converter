import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from converters.siemens_to_ab import convert_siemens_to_ab
from converters.ab_to_siemens import convert_ab_to_siemens


def test_and_siemens_to_ab():
    result = convert_siemens_to_ab("I0.0 AND I0.1 -> Q0.0")
    assert "XIC(I0.0)" in result["converted_code"]
    assert "XIC(I0.1)" in result["converted_code"]
    assert "OTE(Q0.0)" in result["converted_code"]
    assert result["confidence"]["overall"] > 90


def test_not_ab_to_siemens():
    result = convert_ab_to_siemens("XIO(I0.0) OTE(Q0.0)")
    assert "NOT I0.0 -> Q0.0" in result["converted_code"]


def test_set_reset_roundtrip():
    fwd = convert_siemens_to_ab("SET Q0.0\nRESET Q0.1")
    assert "OTL(Q0.0)" in fwd["converted_code"]
    assert "OTU(Q0.1)" in fwd["converted_code"]

    back = convert_ab_to_siemens(fwd["converted_code"])
    assert "SET Q0.0" in back["converted_code"]
    assert "RESET Q0.1" in back["converted_code"]


def test_timer_roundtrip():
    fwd = convert_siemens_to_ab("TON Timer_1 IN:=I0.0 PT:=T#5s")
    assert "TON(Timer_1,5000)" in fwd["converted_code"]


def test_warnings_for_unsupported_line():
    result = convert_siemens_to_ab("NOT_A_REAL_INSTRUCTION")
    assert len(result["warnings"]) == 1
