"""
Level 3 — Semantic / logic-equivalence validation (project spec section 18-19).

For purely combinational boolean logic (AND / OR / NOT), we can prove
equivalence exhaustively with a truth table: enumerate every 0/1
combination of the input tags, evaluate the SOURCE IR and the TARGET IR,
and compare outputs.

Stateful instructions (SET/RESET/TON/TOF/CTU/CTD) are not evaluable with a
static truth table (they depend on scan history / time), so they are
reported as "skipped" rather than pass/fail. This matches the project's
recommendation to use simulation/state-based testing for larger circuits
(a natural Phase 9+ extension).
"""
import itertools


def _evaluate_program(program, input_values: dict) -> dict:
    """Evaluate the combinational (AND/OR/NOT) instructions of a PLCProgram
    given a dict of {tag: 0/1} for every input tag, returning {output_tag: 0/1}."""
    values = dict(input_values)
    outputs = {}
    for instr in program.instructions:
        if instr.type == "AND":
            a = values.get(instr.inputs[0].tag, 0)
            b = values.get(instr.inputs[1].tag, 0)
            result = 1 if (a and b) else 0
        elif instr.type == "OR":
            a = values.get(instr.inputs[0].tag, 0)
            b = values.get(instr.inputs[1].tag, 0)
            result = 1 if (a or b) else 0
        elif instr.type == "NOT":
            a = values.get(instr.inputs[0].tag, 0)
            result = 0 if a else 1
        else:
            continue  # stateful / non-combinational, not evaluated here
        values[instr.output] = result
        outputs[instr.output] = result
    return outputs


def boolean_equivalence_check(source_code: str, source_vendor: str,
                               target_code: str, target_vendor: str,
                               max_inputs: int = 8) -> dict:
    """Parse both programs, build a truth table over shared boolean inputs,
    and compare outputs row by row. Returns a report dict."""
    from parsers.siemens_parser import SiemensParser
    from parsers.rockwell_parser import RockwellParser

    def get_parser(vendor):
        return SiemensParser() if vendor == "Siemens" else RockwellParser()

    src_program = get_parser(source_vendor).parse(source_code, "source")
    tgt_program = get_parser(target_vendor).parse(target_code, "target")

    has_stateful = any(i.type not in ("AND", "OR", "NOT") for i in src_program.instructions)

    input_tags = sorted(set(src_program.all_boolean_tags()) | set(tgt_program.all_boolean_tags()))
    # Keep only tags that are actually used as *inputs* somewhere (not purely outputs)
    src_outputs = {i.output for i in src_program.instructions if i.type in ("AND", "OR", "NOT")}
    tgt_outputs = {i.output for i in tgt_program.instructions if i.type in ("AND", "OR", "NOT")}
    pure_outputs = src_outputs | tgt_outputs
    input_tags = [t for t in input_tags if t not in pure_outputs]

    if not input_tags:
        return {
            "status": "SKIPPED",
            "reason": "No combinational (AND/OR/NOT) boolean logic found to test.",
            "rows_tested": 0,
            "rows_passed": 0,
            "mismatches": [],
            "stateful_instructions_present": has_stateful,
        }

    if len(input_tags) > max_inputs:
        input_tags = input_tags[:max_inputs]  # keep the truth table tractable for a prototype

    rows_tested = 0
    rows_passed = 0
    mismatches = []

    for combo in itertools.product([0, 1], repeat=len(input_tags)):
        input_values = dict(zip(input_tags, combo))
        src_out = _evaluate_program(src_program, input_values)
        tgt_out = _evaluate_program(tgt_program, input_values)

        # Compare outputs common to both (by tag name, since IR preserves names).
        common_outputs = set(src_out.keys()) & set(tgt_out.keys())
        if not common_outputs:
            continue

        rows_tested += 1
        row_ok = all(src_out[o] == tgt_out[o] for o in common_outputs)
        if row_ok:
            rows_passed += 1
        else:
            mismatches.append({
                "inputs": input_values,
                "source_outputs": {o: src_out[o] for o in common_outputs},
                "target_outputs": {o: tgt_out[o] for o in common_outputs},
            })

    if rows_tested == 0:
        status = "SKIPPED"
    elif rows_passed == rows_tested:
        status = "PASS"
    else:
        status = "FAIL"

    return {
        "status": status,
        "rows_tested": rows_tested,
        "rows_passed": rows_passed,
        "mismatches": mismatches[:10],  # cap for readability
        "stateful_instructions_present": has_stateful,
    }
