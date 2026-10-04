"""
Programmatic parallel-corpus generator (spec sections 10-12).

Produces JSONL rows of {source_vendor, target_vendor, source, target, category}
for the basic-logic / timer / counter categories, which can seed the
"~2,600-3,000 paired examples" dataset described in the project plan, and
also serve as a large regression-test set for the rule-based converter.

Usage:
    python generate_dataset.py --count 600 --out train.jsonl
"""
import argparse
import json
import random


def _addr():
    return f"I{random.randint(0, 7)}.{random.randint(0, 7)}"


def _out_addr():
    return f"Q{random.randint(0, 7)}.{random.randint(0, 7)}"


def gen_and():
    a, b, q = _addr(), _addr(), _out_addr()
    return {
        "source": f"{a} AND {b} -> {q}",
        "target": f"XIC({a}) XIC({b}) OTE({q})",
        "category": "basic_logic_and",
    }


def gen_or():
    a, b, q = _addr(), _addr(), _out_addr()
    return {
        "source": f"{a} OR {b} -> {q}",
        "target": f"XIC({a}) OTE({q})\nXIC({b}) OTE({q})",
        "category": "basic_logic_or",
    }


def gen_not():
    a, q = _addr(), _out_addr()
    return {
        "source": f"NOT {a} -> {q}",
        "target": f"XIO({a}) OTE({q})",
        "category": "basic_logic_not",
    }


def gen_set_reset():
    q = _out_addr()
    is_set = random.choice([True, False])
    if is_set:
        return {"source": f"SET {q}", "target": f"OTL({q})", "category": "latch_set"}
    return {"source": f"RESET {q}", "target": f"OTU({q})", "category": "latch_reset"}


def gen_timer():
    name = f"Timer_{random.randint(1, 50)}"
    in_tag = _addr()
    preset_s = random.choice([0.5, 1, 2, 5, 10, 30])
    kind = random.choice(["TON", "TOF"])
    preset_ms = int(preset_s * 1000)
    return {
        "source": f"{kind} {name} IN:={in_tag} PT:=T#{preset_s:g}s",
        "target": f"{kind}({name},{preset_ms})",
        "category": "timer",
    }


def gen_counter():
    name = f"Counter_{random.randint(1, 50)}"
    cu_tag, reset_tag = _addr(), _addr()
    preset = random.randint(1, 100)
    kind = random.choice(["CTU", "CTD"])
    label = "CU" if kind == "CTU" else "CD"
    return {
        "source": f"{kind} {name} {label}:={cu_tag} R:={reset_tag} PV:={preset}",
        "target": f"{kind}({name},{preset})",
        "category": "counter",
    }


GENERATORS = [gen_and, gen_or, gen_not, gen_set_reset, gen_timer, gen_counter]


def generate(count: int):
    rows = []
    for _ in range(count):
        gen = random.choice(GENERATORS)
        row = gen()
        row["source_vendor"] = "Siemens"
        row["target_vendor"] = "Rockwell"
        rows.append(row)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--out", type=str, default="train.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    rows = generate(args.count)
    with open(args.out, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"Wrote {len(rows)} examples to {args.out}")
