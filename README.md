# PLC Converter — AI-Assisted Bidirectional PLC Program Conversion (Siemens ⇄ Allen-Bradley)

A working prototype of the hybrid **compiler + AI** architecture: PLC logic is
parsed into a vendor-neutral **Intermediate Representation (IR)**, converted
with a **rule engine** for known instructions, falls back to an **AI engine**
for anything unrecognized, and is checked by a **truth-table equivalence
validator** before a **confidence score** is reported.

```
Siemens code  --parse-->  IR  --rules/AI-->  IR  --generate-->  Rockwell code
Rockwell code --parse-->  IR  --rules/AI-->  IR  --generate-->  Siemens code
```

## What's implemented (Phases 1–3, 8 of the roadmap)

- **Parsers**: `backend/parsers/siemens_parser.py`, `rockwell_parser.py`
  (simplified textual LAD/ST-style syntax — see docstrings for the exact
  grammar each one accepts).
- **IR**: `backend/ir/models.py`, `builder.py`.
- **Rule engine**: `backend/converters/rules.py` + the two converters
  (`siemens_to_ab.py`, `ab_to_siemens.py`), covering **AND, OR, NOT, SET,
  RESET, TON, TOF, CTU, CTD** in both directions.
- **AI fallback engine**: `backend/ai/inference.py` — calls the Anthropic API
  if `ANTHROPIC_API_KEY` is set, otherwise emits a clearly-labeled
  `/* TODO: manual conversion required */` placeholder so the pipeline still
  completes end-to-end without any API key.
- **Validation**:
  - Level 1 syntax (`validators/syntax.py`)
  - Level 3 semantic/logic equivalence via **exhaustive truth-table testing**
    for combinational (AND/OR/NOT) logic (`validators/logic.py`)
  - Component-weighted **confidence score** (`validators/confidence.py`),
    exactly matching the weighting scheme in the project brief
    (30/20/15/25/10%).
- **Flask API** (`backend/app.py`): `POST /convert`, `POST /validate`,
  `GET /health`.
- **Web dashboard** (`frontend/`): vendor selectors, side-by-side code panes,
  confidence badge, tag-mapping table, warnings, equivalence result.
- **Dataset generator** (`backend/dataset/generate_dataset.py`): produces the
  synthetic parallel corpus described in the brief (JSONL, categorized).
  A 100-row sample is included at `backend/dataset/sample.jsonl`.
- **Tests** (`backend/tests/`): parser, converter, and equivalence tests.

## Quick start

```bash
cd backend
pip install -r requirements.txt   # flask (+ optional anthropic, pytest)
python app.py                     # serves API + frontend on http://localhost:5000
```

Open `http://localhost:5000` in a browser, pick source/target vendor, click
**Load example**, then **CONVERT**.

To run the tests (needs `pytest`, or just run the file bodies with plain
Python — no pytest-specific features are used):

```bash
cd backend
pytest tests/
```

To generate a larger training/regression dataset:

```bash
cd backend/dataset
python generate_dataset.py --count 3000 --out train.jsonl
```

## Example

Siemens in:
```
I0.0 AND I0.1 -> Q0.0
I0.2 OR I0.3 -> Q0.1
NOT I0.4 -> Q0.2
SET Q0.3
RESET Q0.4
TON Timer_1 IN:=I0.0 PT:=T#5s
CTU Counter_1 CU:=I0.0 R:=I0.1 PV:=10
```

Allen-Bradley out (confidence 100%, equivalence PASS on 128/128 truth-table rows):
```
XIC(I0.0) XIC(I0.1) OTE(Q0.0)
XIC(I0.2) OTE(Q0.1)
XIC(I0.3) OTE(Q0.1)
XIO(I0.4) OTE(Q0.2)
OTL(Q0.3)
OTU(Q0.4)
TON(Timer_1,5000)
CTU(Counter_1,10)
```

## Known prototype limitations (intentional — see roadmap below)

- The parsers accept a **simplified textual DSL**, not native `.SCL/.AWL`
  TIA-Portal export or `.L5X` Studio 5000 XML. Swapping in real file-format
  parsers is a drop-in replacement for `SiemensParser`/`RockwellParser` since
  everything downstream only depends on the IR.
- The textual AB form doesn't retain a timer/counter's enable-input tag
  (real ladder would show it as a preceding rung), so an AB→Siemens→AB
  round trip on timers reuses a placeholder tag name (`Start`/`Reset`).
  Preserving this is a small parser change (capture the preceding XIC on
  the same rung).
- SET/RESET (latch) logic and timers/counters are **not** covered by the
  truth-table equivalence check (they're stateful/time-based); the report
  marks these as "skipped" rather than pass/fail, matching the brief's
  suggestion to use simulation/state-based testing for those cases.
- The AI engine is a stub unless you supply `ANTHROPIC_API_KEY` — see
  `backend/ai/inference.py` and `prompts.py` to swap in any other LLM
  provider's SDK.

## Suggested next steps (Phases 4–10 from the original plan)

1. Add native file I/O: `.L5X` (Studio 5000 XML) and `.SCL`/`.AWL` (TIA
   Portal export) readers/writers around the existing parsers/generators.
2. Expand the IR and rule tables to branching/nested ladder logic, not just
   single-rung AND/OR/NOT.
3. Wire a real LLM into `ai/inference.py` for anything the rule engine can't
   handle, and prompt it to also return an `explanation` field for the UI.
4. Extend `validators/logic.py` to a state-based simulator (step the scan
   cycle over multiple cycles) so SET/RESET/timers/counters can be verified
   too, not just skipped.
5. Grow `dataset/generate_dataset.py` to ~2,600–3,000 examples across all the
   categories in the brief (motor control, interlocks, sequencing, analog,
   alarms), and use it as a regression suite: run every row through the
   converter and report syntax/instruction/tag/equivalence accuracy — this
   is the material for the results section of a final-year report or paper.

## Safety note

Converted logic must be reviewed and tested inside the appropriate Siemens
(TIA Portal) or Rockwell (Studio 5000) engineering environment — including
offline simulation and a controlled commissioning test — before being
deployed to any real PLC or connected machinery. This tool is an educational
prototype, not a certified industrial conversion product.
