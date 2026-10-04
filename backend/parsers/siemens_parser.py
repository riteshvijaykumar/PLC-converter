"""
Parser for a simplified textual Siemens (TIA Portal style) representation.

Supported line forms (one instruction per line, case-insensitive keywords):

    I0.0 AND I0.1 -> Q0.0
    I0.0 OR  I0.1 -> Q0.0
    NOT I0.0 -> Q0.0
    SET Q0.0
    RESET Q0.0
    TON Timer_1 IN:=Start PT:=T#5s
    TOF Timer_1 IN:=Start PT:=T#5s
    CTU Counter_1 CU:=Start R:=Reset PV:=10
    CTD Counter_1 CD:=Start R:=Reset PV:=10

This is a teaching/prototype-grade parser (regex/line based), not a full
TIA Portal SCL/LAD/STL grammar. It is intended to be extended in later
project phases per the recommended development sequence.
"""
import re
from ir.models import PLCProgram, Instruction, Contact

_AND_RE = re.compile(r"^(?P<a>\S+)\s+AND\s+(?P<b>\S+)\s*->\s*(?P<out>\S+)$", re.I)
_OR_RE = re.compile(r"^(?P<a>\S+)\s+OR\s+(?P<b>\S+)\s*->\s*(?P<out>\S+)$", re.I)
_NOT_RE = re.compile(r"^NOT\s+(?P<a>\S+)\s*->\s*(?P<out>\S+)$", re.I)
_SET_RE = re.compile(r"^SET\s+(?P<out>\S+)$", re.I)
_RESET_RE = re.compile(r"^RESET\s+(?P<out>\S+)$", re.I)
_TIMER_RE = re.compile(
    r"^(?P<kind>TON|TOF)\s+(?P<name>\S+)\s+IN:=\s*(?P<in>\S+)\s+PT:=\s*T#(?P<preset>[\d.]+)s$",
    re.I,
)
_COUNTER_RE = re.compile(
    r"^(?P<kind>CTU|CTD)\s+(?P<name>\S+)\s+C[UD]:=\s*(?P<cu>\S+)\s+R:=\s*(?P<reset>\S+)\s+PV:=\s*(?P<preset>\d+)$",
    re.I,
)


class SiemensParser:
    vendor = "Siemens"

    def parse(self, code: str, program_name: str = "SiemensProgram") -> PLCProgram:
        program = PLCProgram(name=program_name, vendor=self.vendor)

        for raw_line in code.strip().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue

            m = _AND_RE.match(line)
            if m:
                program.instructions.append(Instruction(
                    type="AND",
                    inputs=[Contact(m.group("a")), Contact(m.group("b"))],
                    output=m.group("out"),
                    raw_source=line,
                ))
                continue

            m = _OR_RE.match(line)
            if m:
                program.instructions.append(Instruction(
                    type="OR",
                    inputs=[Contact(m.group("a")), Contact(m.group("b"))],
                    output=m.group("out"),
                    raw_source=line,
                ))
                continue

            m = _NOT_RE.match(line)
            if m:
                program.instructions.append(Instruction(
                    type="NOT",
                    inputs=[Contact(m.group("a"), "NC")],
                    output=m.group("out"),
                    raw_source=line,
                ))
                continue

            m = _SET_RE.match(line)
            if m:
                program.instructions.append(Instruction(type="SET", output=m.group("out"), raw_source=line))
                continue

            m = _RESET_RE.match(line)
            if m:
                program.instructions.append(Instruction(type="RESET", output=m.group("out"), raw_source=line))
                continue

            m = _TIMER_RE.match(line)
            if m:
                preset_ms = int(float(m.group("preset")) * 1000)
                program.instructions.append(Instruction(
                    type=m.group("kind").upper(),
                    inputs=[Contact(m.group("in"))],
                    output=m.group("name"),
                    parameters={"preset_ms": preset_ms},
                    raw_source=line,
                ))
                continue

            m = _COUNTER_RE.match(line)
            if m:
                program.instructions.append(Instruction(
                    type=m.group("kind").upper(),
                    inputs=[Contact(m.group("cu")), Contact(m.group("reset"), "RESET")],
                    output=m.group("name"),
                    parameters={"preset": int(m.group("preset"))},
                    raw_source=line,
                ))
                continue

            # Nothing matched -> flag for AI engine / manual review.
            program.unsupported_lines.append(line)

        return program
