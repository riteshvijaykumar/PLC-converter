"""
Parser for a simplified textual Allen-Bradley / Rockwell (Studio 5000 style)
ladder representation.

Supported line forms (one rung per line):

    XIC(I0.0) XIC(I0.1) OTE(Q0.0)          -> AND
    XIC(I0.0) OTE(Q0.0)                    -> single contact (may combine into OR)
    XIC(I0.0) OTE(Q0.0)
    XIC(I0.1) OTE(Q0.0)                    -> two rungs, same output -> OR (parallel branch)
    XIO(I0.0) OTE(Q0.0)                    -> NOT
    OTL(Q0.0)                              -> SET / latch
    OTU(Q0.0)                              -> RESET / unlatch
    TON(Timer_1,5000)                      -> on-delay timer, preset in ms
    TOF(Timer_1,5000)
    CTU(Counter_1,10)                      -> up counter, preset value
    CTD(Counter_1,10)

Like the Siemens parser, this is prototype-grade: it covers the instruction
set enumerated in the project's rule-based mapping table and is meant to be
extended (native .L5X import, branch/rung XML) in later phases.
"""
import re
from ir.models import PLCProgram, Instruction, Contact

_XIC_RE = re.compile(r"XIC\((?P<tag>[^)]+)\)")
_XIO_RE = re.compile(r"XIO\((?P<tag>[^)]+)\)")
_OTE_RE = re.compile(r"OTE\((?P<tag>[^)]+)\)")
_OTL_RE = re.compile(r"^OTL\((?P<tag>[^)]+)\)$", re.I)
_OTU_RE = re.compile(r"^OTU\((?P<tag>[^)]+)\)$", re.I)
_TIMER_RE = re.compile(r"^(?P<kind>TON|TOF)\((?P<name>[^,]+),(?P<preset>\d+)(?:,\d+)?\)$", re.I)
_COUNTER_RE = re.compile(r"^(?P<kind>CTU|CTD)\((?P<name>[^,]+),(?P<preset>\d+)(?:,\d+)?\)$", re.I)


class RockwellParser:
    vendor = "Rockwell"

    def parse(self, code: str, program_name: str = "RockwellProgram") -> PLCProgram:
        program = PLCProgram(name=program_name, vendor=self.vendor)
        raw_instructions = []  # temp list before OR-combination pass

        for raw_line in code.strip().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue

            m = _OTL_RE.match(line)
            if m:
                raw_instructions.append(Instruction(type="SET", output=m.group("tag").strip(), raw_source=line))
                continue

            m = _OTU_RE.match(line)
            if m:
                raw_instructions.append(Instruction(type="RESET", output=m.group("tag").strip(), raw_source=line))
                continue

            m = _TIMER_RE.match(line)
            if m:
                # timer's enable input, if present, would appear as a preceding XIC on
                # the same rung in real ladder; the simplified textual form assumes
                # an implicit "always scan" or an already-captured XIC earlier.
                raw_instructions.append(Instruction(
                    type=m.group("kind").upper(),
                    output=m.group("name").strip(),
                    parameters={"preset_ms": int(m.group("preset"))},
                    raw_source=line,
                ))
                continue

            m = _COUNTER_RE.match(line)
            if m:
                raw_instructions.append(Instruction(
                    type=m.group("kind").upper(),
                    output=m.group("name").strip(),
                    parameters={"preset": int(m.group("preset"))},
                    raw_source=line,
                ))
                continue

            xic_tags = [t.strip() for t in _XIC_RE.findall(line)]
            xio_tags = [t.strip() for t in _XIO_RE.findall(line)]
            ote_tags = [t.strip() for t in _OTE_RE.findall(line)]

            if ote_tags and (xic_tags or xio_tags):
                output = ote_tags[0]
                contacts = [Contact(t, "NO") for t in xic_tags] + [Contact(t, "NC") for t in xio_tags]

                if len(contacts) == 1 and contacts[0].contact_type == "NC":
                    raw_instructions.append(Instruction(type="NOT", inputs=contacts, output=output, raw_source=line))
                elif len(contacts) == 1:
                    # Single NO contact -> could be a plain pass-through or one leg
                    # of an OR; the combination pass below merges same-output rungs.
                    raw_instructions.append(Instruction(type="OR_LEG", inputs=contacts, output=output, raw_source=line))
                elif len(contacts) >= 2:
                    raw_instructions.append(Instruction(type="AND", inputs=contacts[:2], output=output, raw_source=line))
                continue

            program.unsupported_lines.append(line)

        # Combine consecutive OR_LEG rungs that share the same output into one OR.
        instructions = []
        i = 0
        while i < len(raw_instructions):
            instr = raw_instructions[i]
            if instr.type == "OR_LEG":
                same_output = [instr]
                j = i + 1
                while j < len(raw_instructions) and raw_instructions[j].type == "OR_LEG" \
                        and raw_instructions[j].output == instr.output:
                    same_output.append(raw_instructions[j])
                    j += 1
                if len(same_output) >= 2:
                    combined_inputs = [leg.inputs[0] for leg in same_output[:2]]
                    raw = " | ".join(leg.raw_source for leg in same_output)
                    instructions.append(Instruction(type="OR", inputs=combined_inputs, output=instr.output, raw_source=raw))
                else:
                    # Lone single-contact rung: treat as AND of contact with itself's
                    # semantics is meaningless, so represent it as a pass-through AND
                    # with the same tag twice (kept simple for the prototype).
                    instructions.append(Instruction(type="AND", inputs=[instr.inputs[0], instr.inputs[0]], output=instr.output, raw_source=instr.raw_source))
                i = j
            else:
                instructions.append(instr)
                i += 1

        program.instructions = instructions
        return program
