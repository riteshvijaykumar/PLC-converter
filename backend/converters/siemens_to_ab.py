from parsers.siemens_parser import SiemensParser
from converters.rules import SUPPORTED_TYPES
from ai.inference import ai_suggest_conversion
from validators.confidence import calculate_confidence
from validators.logic import boolean_equivalence_check


def _instruction_to_ab(instr) -> str:
    t = instr.type
    if t == "AND":
        a, b = instr.inputs[0].tag, instr.inputs[1].tag
        return f"XIC({a}) XIC({b}) OTE({instr.output})"
    if t == "OR":
        a, b = instr.inputs[0].tag, instr.inputs[1].tag
        return f"XIC({a}) OTE({instr.output})\nXIC({b}) OTE({instr.output})"
    if t == "NOT":
        a = instr.inputs[0].tag
        return f"XIO({a}) OTE({instr.output})"
    if t == "SET":
        return f"OTL({instr.output})"
    if t == "RESET":
        return f"OTU({instr.output})"
    if t in ("TON", "TOF"):
        preset = instr.parameters.get("preset_ms", 0)
        in_tag = instr.inputs[0].tag if instr.inputs else ""
        comment = f"// enable: XIC({in_tag})\n" if in_tag else ""
        return f"{comment}{t}({instr.output},{preset})"
    if t in ("CTU", "CTD"):
        preset = instr.parameters.get("preset", 0)
        return f"{t}({instr.output},{preset})"
    return None


def convert_siemens_to_ab(code: str, program_name: str = "Program1") -> dict:
    parser = SiemensParser()
    program = parser.parse(code, program_name)

    converted_lines = []
    warnings = []
    tag_mapping = []
    unresolved = list(program.unsupported_lines)
    ai_used_count = 0
    total_instructions = len(program.instructions) + len(program.unsupported_lines)

    for instr in program.instructions:
        if instr.type in SUPPORTED_TYPES:
            ab_line = _instruction_to_ab(instr)
            converted_lines.append(ab_line)
            for c in instr.inputs:
                tag_mapping.append({"siemens_tag": c.tag, "ab_tag": c.tag})
            if instr.output:
                tag_mapping.append({"siemens_tag": instr.output, "ab_tag": instr.output})
        else:
            suggestion = ai_suggest_conversion(instr.to_dict(), "Siemens", "Rockwell")
            converted_lines.append(f"// AI-SUGGESTED (verify manually):\n{suggestion['converted_code']}")
            warnings.append(f"Instruction type '{instr.type}' used AI-assisted conversion: {suggestion['note']}")
            ai_used_count += 1

    for line in unresolved:
        suggestion = ai_suggest_conversion({"raw_source": line}, "Siemens", "Rockwell")
        converted_lines.append(f"// AI-SUGGESTED (verify manually):\n{suggestion['converted_code']}")
        warnings.append(f"Unparsed line sent to AI engine: '{line}'")
        ai_used_count += 1

    converted_code = "\n".join(converted_lines)

    equivalence = boolean_equivalence_check(
        source_code=code, source_vendor="Siemens",
        target_code=converted_code, target_vendor="Rockwell",
    )

    confidence = calculate_confidence(
        total_instructions=max(total_instructions, 1),
        rule_based_count=total_instructions - ai_used_count,
        ai_based_count=ai_used_count,
        equivalence_result=equivalence,
        unresolved_count=len(unresolved),
    )

    # Deduplicate tag mapping while preserving order.
    seen = set()
    deduped_mapping = []
    for m in tag_mapping:
        key = (m["siemens_tag"], m["ab_tag"])
        if key not in seen:
            seen.add(key)
            deduped_mapping.append(m)

    return {
        "source_vendor": "Siemens",
        "target_vendor": "Rockwell",
        "converted_code": converted_code,
        "tag_mapping": deduped_mapping,
        "warnings": warnings,
        "confidence": confidence,
        "equivalence": equivalence,
        "ir": program.to_dict(),
    }
