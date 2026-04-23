# LangGraph Risk Workflow Skeleton (Graph API)

This repository contains a **runnable skeleton** for an 8-step risk workflow using LangGraph Graph API.
The code follows an official LangGraph-style organization:
- explicit state schema
- isolated node functions
- separate routing functions
- graph builder/compile entry
- persistent checkpointer (SQLite)

The current version intentionally keeps business logic as placeholders.

## 1. Workflow Scope

Implemented flow:

1. `parse_inspection_rules`
2. `build_initial_kg`
3. `fetch_and_analyze_monitoring`
4. `reconstruct_kg_with_anomaly`
5. `generate_risk_grade_and_basis`
6. `validate_with_history`
7. `human_review`
8. `update_inspection_rules`

Flow semantics:
- `START -> 1 -> 2 -> 3`
- after step 3:
  - anomaly: `4 -> 5`
  - no anomaly: `5`
- then `6 -> 7`
- after step 7:
  - approved: `END`
  - rejected: `8 -> 2` (loop until approved)

## 2. Project Structure

```text
.
|- main.py
|- graph.py
|- README.md
|- requirements.txt
|- workflow.mmd
|- explain/
|  |- AGENTS.md
|  `- workflow.mmd
`- risk_workflow/
   |- __init__.py
   |- state.py
   |- nodes.py
   |- rules/
   |  |- __init__.py
   |  |- node1/
   |  |  |- __init__.py
   |  |  `- __main__.py
   |  |- node2/
   |  |  |- __init__.py
   |  |  `- __main__.py
   |  |- node3/
   |  |  `- __init__.py
   |  |- node4/
   |  |  `- __init__.py
   |  |- node5/
   |  |  `- __init__.py
   |  |- node6/
   |  |  `- __init__.py
   |  |- node7/
   |  |  `- __init__.py
   |  `- node8/
   |     `- __init__.py
   |- routes.py
   `- graph.py
```

## 3. Environment Setup

Use Python 3.10 and `.venv`:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
```

## 4. Run Demo

```powershell
python main.py
```

What `main.py` does:
- builds a sample state
- uses SQLite checkpointer at `data/checkpoints/risk_workflow.sqlite`
- generates a fresh `thread_id` each run (avoids previous-run interference)
- pauses at `human_review` via `interrupt(...)`
- resumes twice with demo decisions
- resume #1: `rejected` (triggers `update_inspection_rules` and loop)
- resume #2: `approved` (finishes at `END`)
- prints final state

Run the review UI with the local workflow API:

```powershell
python -m risk_workflow.grading.server --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/front/
```

The API exposes:
- `POST /api/workflow/start`: runs one risk point until node 7 pauses and returns the node 6 review payload.
- `POST /api/workflow/review`: resumes with the manual review result. Correct reviews end the workflow; incorrect reviews trigger rule revision in node 8 and rerun the same risk point.

## 5. Persistent Memory (SQLite + thread_id)

The graph uses:
- `langgraph.checkpoint.sqlite.SqliteSaver`
- DB file: `data/checkpoints/risk_workflow.sqlite`

With the same `thread_id`, LangGraph resumes from that thread's latest checkpointed state.
With a different `thread_id`, it starts a new independent state history.

## 6. Human Review Node Design

`human_review` is implemented with real LangGraph human-in-the-loop semantics.

Current behavior:
- node calls `interrupt(...)` with review context payload
- graph execution pauses and returns `__interrupt__`
- caller resumes with `Command(resume={"decision": "approved" | "rejected", "comment": "..."})`
- caller must use the same `thread_id` when resuming
- routing after resume: `approved -> END`
- routing after resume: `rejected -> update_inspection_rules -> build_initial_kg -> ... -> human_review`

Minimal external resume example:

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "case-123"}}
graph.invoke(initial_state, config=config)  # pauses at interrupt
graph.invoke(
    Command(resume={"decision": "approved", "comment": "looks good"}),
    config=config,
)
```

## 7. Notes for Next Iteration

- Keep node signatures and returned keys stable.
- Replace placeholder internals in `risk_workflow/rules/node2 ... node8` gradually.
- Do not move routing logic into nodes; keep it in `risk_workflow/routes.py`.

## 8. Node1 Rule Extraction

Node1 implementation location:
- `risk_workflow/rules/node1/__init__.py`

What it does:
- reads supported docs (`.pdf`, `.txt`, `.md`) from `data/docs`
- injects document text into the extraction prompt
- calls LLM with one request per document and parses/normalizes JSON result
- graph node1 (`parse_inspection_rules`) also merges optional
  `raw_rule_docs` / `inspection_text` from graph state into the same prompt
- graph node1 auto-persists output to `risk_workflow/outputs/node1` by default

Config source:
- use `.env` in project root
- currently expected keys:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `OPENAI_EMBEDDING_MODEL`

CLI run:

```powershell
python -m risk_workflow.rules.node1 --docs-dir data/docs --output-dir data/parsed_rules/node1
```

Dry-run:

```powershell
python -m risk_workflow.rules.node1 --docs-dir data/docs --dry-run
```

## 9. Node2 EDC Initial KG

Node2 implementation location:
- `risk_workflow/rules/node2/__init__.py`

What it does:
- runs bundled EDC pipeline (`risk_workflow/rules/node2/edc-main/edc-main`)
- uses `.env` for both LLM and embedding:
  - `OPENAI_MODEL` (e.g. `glm-5`)
  - `OPENAI_EMBEDDING_MODEL` (e.g. `embedding-3`)
- writes run artifacts under `risk_workflow/outputs/node2/<case_id>_<timestamp>`

Standalone run:

```powershell
python -m risk_workflow.rules.node2 --inspection-text "广西某高速边坡在连续降雨后出现裂缝与渗水。"
```
