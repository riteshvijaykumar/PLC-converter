import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers.siemens_parser import SiemensParser
from parsers.rockwell_parser import RockwellParser


def test_siemens_and():
    p = SiemensParser().parse("I0.0 AND I0.1 -> Q0.0")
    assert len(p.instructions) == 1
    assert p.instructions[0].type == "AND"
    assert p.instructions[0].output == "Q0.0"


def test_siemens_set_reset():
    p = SiemensParser().parse("SET Q0.0\nRESET Q0.1")
    assert [i.type for i in p.instructions] == ["SET", "RESET"]


def test_siemens_timer():
    p = SiemensParser().parse("TON Timer_1 IN:=I0.0 PT:=T#5s")
    assert p.instructions[0].type == "TON"
    assert p.instructions[0].parameters["preset_ms"] == 5000


def test_rockwell_and():
    p = RockwellParser().parse("XIC(I0.0) XIC(I0.1) OTE(Q0.0)")
    assert p.instructions[0].type == "AND"


def test_rockwell_or_combines_rungs():
    code = "XIC(I0.0) OTE(Q0.0)\nXIC(I0.1) OTE(Q0.0)"
    p = RockwellParser().parse(code)
    assert p.instructions[0].type == "OR"


def test_rockwell_not():
    p = RockwellParser().parse("XIO(I0.0) OTE(Q0.0)")
    assert p.instructions[0].type == "NOT"


def test_unsupported_line_flagged():
    p = SiemensParser().parse("SOME_GARBLED_LINE_NOT_IN_GRAMMAR")
    assert len(p.unsupported_lines) == 1
