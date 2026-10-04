"""
Universal PLC Intermediate Representation (IR).

Every parser (Siemens, Rockwell/AB) converts source code into a list of
Instruction objects wrapped in a PLCProgram. Every generator consumes the
same IR to produce target-vendor code. This is what lets the same core
logic be reused for both Siemens->AB and AB->Siemens conversion.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Contact:
    """A single input reference inside a boolean instruction."""
    tag: str
    contact_type: str = "NO"  # "NO" (normally open) or "NC" (normally closed)

    def to_dict(self):
        return {"tag": self.tag, "type": self.contact_type}


@dataclass
class Instruction:
    """
    One logical unit of PLC logic in vendor-neutral form.

    type: "AND" | "OR" | "NOT" | "SET" | "RESET" | "TON" | "TOF" | "CTU" | "CTD"
    inputs: list[Contact]            (for boolean ops)
    output: str                      (coil / tag being written)
    parameters: dict                 (timer/counter presets, etc.)
    raw_source: str                  (original line, kept for traceability)
    """
    type: str
    inputs: List[Contact] = field(default_factory=list)
    output: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_source: str = ""

    def to_dict(self):
        return {
            "type": self.type,
            "inputs": [c.to_dict() for c in self.inputs],
            "output": self.output,
            "parameters": self.parameters,
            "raw_source": self.raw_source,
        }


@dataclass
class Tag:
    name: str
    data_type: str = "BOOL"
    address: Optional[str] = None


@dataclass
class PLCProgram:
    name: str
    vendor: str  # "Siemens" | "Rockwell"
    instructions: List[Instruction] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=list)
    unsupported_lines: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "vendor": self.vendor,
            "instructions": [i.to_dict() for i in self.instructions],
            "tags": [t.__dict__ for t in self.tags],
            "unsupported_lines": self.unsupported_lines,
        }

    def all_boolean_tags(self) -> List[str]:
        """Collect every distinct boolean tag referenced (inputs + outputs)."""
        seen = []
        for instr in self.instructions:
            if instr.type in ("AND", "OR", "NOT", "SET", "RESET"):
                for c in instr.inputs:
                    if c.tag not in seen:
                        seen.append(c.tag)
                if instr.output and instr.output not in seen:
                    seen.append(instr.output)
        return seen
