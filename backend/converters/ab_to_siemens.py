from parsers.rockwell_parser import RockwellParser
from converters.rules import SUPPORTED_TYPES
from ai.inference import ai_suggest_conversion
from validators.confidence import calculate_confidence
from validators.logic import boolean_equivalence_check


def _instruction_to_siemens(instr) -> str:
    t = instr.type
    if t == "AND":
        a, b = instr.inputs[0].tag, instr.inputs[1].tag
        return f"{a} AND {b} -> {instr.output}"
    if t == "OR":
        a, b = instr.inputs[0].tag, instr.inputs[1].tag
        return f"{a} OR {b} -> {instr.output}"
    if t == "NOT":
        a = instr.inputs[0].tag
        return f"NOT {a} -> {instr.output}"
    if t == "SET":
        return f"SET {instr.output}"
    if t == "RESET":
        return f"RESET {instr.output}"
    if t in ("TON", "TOF"):
        preset_s = instr.parameters.get("preset_ms", 0) / 1000
        in_tag = instr.inputs[0].tag if instr.inputs else "Start"
        return f"{t} {instr.output} IN:={in_tag} PT:=T#{preset_s:g}s"
    if t in ("CTU", "CTD"):
        preset = instr.parameters.get("preset", 0)
        cu_tag = instr.inputs[0].tag if instr.inputs else "Start"
        reset_tag = instr.inputs[1].tag if len(instr.inputs) > 1 else "Reset"
        cu_label = "CU" if t == "CTU" else "CD"
        return f"{t} {instr.output} {cu_label}:={cu_tag} R:={reset_tag} PV:={preset}"
    return None


def convert_ab_to_siemens(code: str, program_name: str = "Program1") -> dict:
    parser = RockwellParser()
    program = parser.parse(code, program_name)

    converted_lines = []
    warnings = []
    tag_mapping = []
    unresolved = list(program.unsupported_lines)
    ai_used_count = 0
    total_instructions = len(program.instructions) + len(program.unsupported_lines)

    for instr in program.instructions:
        if instr.type in SUPPORTED_TYPES:
            siemens_line = _instruction_to_siemens(instr)
            converted_lines.append(siemens_line)
            for c in instr.inputs:
                tag_mapping.append({"ab_tag": c.tag, "siemens_tag": c.tag})
            if instr.output:
                tag_mapping.append({"ab_tag": instr.output, "siemens_tag": instr.output})
        else:
            suggestion = ai_suggest_conversion(instr.to_dict(), "Rockwell", "Siemens")
            converted_lines.append(f"// AI-SUGGESTED (verify manually):\n{suggestion['converted_code']}")
            warnings.append(f"Instruction type '{instr.type}' used AI-assisted conversion: {suggestion['note']}")
            ai_used_count += 1

    for line in unresolved:
        suggestion = ai_suggest_conversion({"raw_source": line}, "Rockwell", "Siemens")
        converted_lines.append(f"// AI-SUGGESTED (verify manually):\n{suggestion['converted_code']}")
        warnings.append(f"Unparsed line sent to AI engine: '{line}'")
        ai_used_count += 1

    converted_code = "\n".join(converted_lines)

    equivalence = boolean_equivalence_check(
        source_code=code, source_vendor="Rockwell",
        target_code=converted_code, target_vendor="Siemens",
    )

    confidence = calculate_confidence(
        total_instructions=max(total_instructions, 1),
        rule_based_count=total_instructions - ai_used_count,
        ai_based_count=ai_used_count,
        equivalence_result=equivalence,
        unresolved_count=len(unresolved),
    )

    seen = set()
    deduped_mapping = []
    for m in tag_mapping:
        key = (m["ab_tag"], m["siemens_tag"])
        if key not in seen:
            seen.add(key)
            deduped_mapping.append(m)

    return {
        "source_vendor": "Rockwell",
        "target_vendor": "Siemens",
        "converted_code": converted_code,
        "tag_mapping": deduped_mapping,
        "warnings": warnings,
        "confidence": confidence,
        "equivalence": equivalence,
        "ir": program.to_dict(),
    }
