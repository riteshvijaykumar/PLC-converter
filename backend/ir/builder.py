"""Small helpers for assembling IR objects from parser matches."""
from .models import Contact, Instruction


def make_and(a: str, b: str, output: str, raw: str = "") -> Instruction:
    return Instruction(type="AND", inputs=[Contact(a), Contact(b)], output=output, raw_source=raw)


def make_or(a: str, b: str, output: str, raw: str = "") -> Instruction:
    return Instruction(type="OR", inputs=[Contact(a), Contact(b)], output=output, raw_source=raw)


def make_not(a: str, output: str, raw: str = "") -> Instruction:
    return Instruction(type="NOT", inputs=[Contact(a, "NC")], output=output, raw_source=raw)


def make_set(output: str, raw: str = "") -> Instruction:
    return Instruction(type="SET", output=output, raw_source=raw)


def make_reset(output: str, raw: str = "") -> Instruction:
    return Instruction(type="RESET", output=output, raw_source=raw)


def make_timer(kind: str, name: str, in_tag: str, preset_ms: int, raw: str = "") -> Instruction:
    return Instruction(
        type=kind,  # "TON" or "TOF"
        inputs=[Contact(in_tag)],
        output=name,
        parameters={"preset_ms": preset_ms},
        raw_source=raw,
    )


def make_counter(kind: str, name: str, cu_tag: str, reset_tag: str, preset: int, raw: str = "") -> Instruction:
    return Instruction(
        type=kind,  # "CTU" or "CTD"
        inputs=[Contact(cu_tag), Contact(reset_tag, "RESET")],
        output=name,
        parameters={"preset": preset},
        raw_source=raw,
    )
