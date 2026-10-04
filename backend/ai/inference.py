"""
AI conversion engine (Module 5, spec section 8-9).

For instructions the rule engine does NOT recognize, this module is the
fallback: it should call an LLM (Claude/GPT/Gemini/local code model) with
the structured prompt in prompts.py and parse a JSON response.

To keep the prototype runnable with zero external dependencies / API keys,
`ai_suggest_conversion` first tries a real API call (if ANTHROPIC_API_KEY is
set) and otherwise falls back to a clearly-labeled heuristic placeholder so
the rest of the pipeline (validation, confidence scoring, reporting) still
has something to work with end-to-end. Replace `_call_llm` with your chosen
provider's SDK call for a production/thesis-grade deployment.
"""
import json
import os

from ai.prompts import SYSTEM_PROMPT, USER_TEMPLATE


def _call_llm(system_prompt: str, user_prompt: str):
    """Attempt a real LLM call if an API key is configured. Returns the raw
    text response, or None if no provider is configured / the call fails."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # pip install anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))
    except Exception as exc:  # network / SDK / auth errors -> fall back gracefully
        print(f"[ai_engine] LLM call failed, using offline fallback: {exc}")
        return None


def _offline_fallback(ir_or_line: dict, source_vendor: str, target_vendor: str) -> dict:
    """Deterministic placeholder used when no LLM is configured. It makes the
    unsupported instruction visible in the output rather than silently
    dropping it, and is clearly flagged as needing manual/engineer review."""
    raw = ir_or_line.get("raw_source") or json.dumps(ir_or_line)
    return {
        "converted_code": f"/* TODO: manual conversion required for: {raw} */",
        "note": "No AI provider configured (set ANTHROPIC_API_KEY) — placeholder emitted.",
        "warnings": ["Requires manual engineering review before deployment."],
    }


def ai_suggest_conversion(ir_or_line: dict, source_vendor: str, target_vendor: str) -> dict:
    system_prompt = SYSTEM_PROMPT.format(source_vendor=source_vendor, target_vendor=target_vendor)
    user_prompt = USER_TEMPLATE.format(
        source_vendor=source_vendor,
        target_vendor=target_vendor,
        ir_json=json.dumps(ir_or_line, indent=2),
    )

    raw_response = _call_llm(system_prompt, user_prompt)
    if raw_response:
        try:
            cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(cleaned)
            parsed.setdefault("warnings", [])
            return parsed
        except Exception as exc:
            print(f"[ai_engine] Could not parse LLM JSON response: {exc}")

    return _offline_fallback(ir_or_line, source_vendor, target_vendor)
