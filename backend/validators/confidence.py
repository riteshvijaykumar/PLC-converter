"""
Confidence scoring (project spec section 25).

confidence = instruction_score*0.30 + syntax_score*0.20 + tag_score*0.15
           + equivalence_score*0.25 + ai_score*0.10

This is a defensible, component-wise methodology rather than an
AI-reported single number, so it can be explained/justified in a report.
"""


def calculate_confidence(total_instructions: int, rule_based_count: int,
                          ai_based_count: int, equivalence_result: dict,
                          unresolved_count: int) -> dict:
    total_instructions = max(total_instructions, 1)

    instruction_score = rule_based_count / total_instructions

    # Syntax score: penalize unresolved/unparsed lines.
    syntax_score = 1.0 - (unresolved_count / total_instructions)
    syntax_score = max(syntax_score, 0.0)

    # Tag mapping is trivially 1:1 in this prototype (names preserved),
    # so tag_score tracks how much of the program mapped cleanly at all.
    tag_score = instruction_score

    eq_status = equivalence_result.get("status")
    if eq_status == "PASS":
        equivalence_score = 1.0
    elif eq_status == "FAIL":
        rows_tested = equivalence_result.get("rows_tested") or 1
        equivalence_score = equivalence_result.get("rows_passed", 0) / rows_tested
    else:  # SKIPPED - no combinational logic to test, treat as neutral
        equivalence_score = 0.75

    # AI score: rule-based instructions are trusted more than AI guesses.
    ai_score = rule_based_count / total_instructions

    weighted = (
        instruction_score * 0.30
        + syntax_score * 0.20
        + tag_score * 0.15
        + equivalence_score * 0.25
        + ai_score * 0.10
    )

    return {
        "overall": round(weighted * 100, 1),
        "components": {
            "instruction_score": round(instruction_score * 100, 1),
            "syntax_score": round(syntax_score * 100, 1),
            "tag_score": round(tag_score * 100, 1),
            "equivalence_score": round(equivalence_score * 100, 1),
            "ai_score": round(ai_score * 100, 1),
        },
        "rule_based_instructions": rule_based_count,
        "ai_based_instructions": ai_based_count,
    }
