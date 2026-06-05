# ConfigForge AI

**Compiler-style AI software generator**

ConfigForge AI converts natural language product requests into a validated, repairable, runtime-aware application configuration. It is built as an engineered compiler pipeline, not as a single prompt-to-JSON demo.

## Problem Understanding

Natural language app builders can produce impressive text, but software generation fails when UI, API, database, auth, and business logic drift apart. This project treats the prompt as source code and compiles it through typed intermediate stages into an executable app blueprint.

## Why This Is Not Prompt Engineering

The system is not `prompt -> one LLM call -> JSON`. It uses deterministic local generation by default, typed schemas, strict validation, partial repair, runtime simulation, and an evaluation harness. Optional LLM support can be added later, but correctness is enforced locally.

## Architecture Diagram

```text
User Prompt
↓
Intent Extraction
↓
System Design Layer
↓
Schema Generation
↓
Refinement Layer
↓
Validation Engine
↓
Repair Engine
↓
Runtime Simulator
↓
Executable App Config
```

## Pipeline Stages

- `IntentExtractor`: parses domain, goal, features, entities, roles, auth, payments, analytics, premium, ambiguities, conflicts, and missing details.
- `SystemDesigner`: creates architecture modules, entities, flows, roles, access model, risk notes, and business-rule summaries.
- `SchemaGenerator`: generates UI pages/forms, API endpoints, database tables/relationships, auth roles/permissions, and business logic.
- `RefinementLayer`: deduplicates surfaces and normalizes permissions/business rules before validation.
- `ConfigValidator`: performs strict structural and semantic checks across UI, API, DB, auth, and rules.
- `RepairEngine`: applies localized partial patches and records repair history.
- `RuntimeSimulator`: simulates routes, rendering, API binding, DB creation, relationships, auth, permissions, premium checks, analytics checks, and business-rule compilation.
- `Evaluator`: runs the required 20 prompts and writes JSON/Markdown reports.

## Strict Schema Contract

Every `/generate` response includes:

`pipeline`, `app`, `assumptions`, `intent`, `design`, `entities`, `ui`, `api`, `database`, `auth`, `business_logic`, `validation`, `repair_history`, `execution`, and `quality_metrics`.

## Validation Engine

The validator catches invalid JSON, missing sections, type/schema errors, missing form endpoints, missing UI/API entities, missing DB tables or fields, invalid computed fields, missing primary keys, bad relationships, missing roles or permissions, invalid permission role references, admin pages without admin role, analytics pages without `read:analytics`, payment pages without billing permissions, premium pages without premium rules, duplicate routes/endpoints/tables, orphan entities, plain password storage, missing login/users table, and missing role-access business logic.

## Repair Engine

Repair is partial, not full regeneration. Examples:

- Missing table: add only that table.
- Missing primary key: add only `id` primary key.
- Missing endpoint: add only required endpoint.
- Missing role/permission: add only the missing auth record.
- Plain password storage: replace with `password_hash` and mark password as computed/auth-only.
- Premium rule missing: add only premium gating rule.
- Duplicate route: rename safely.

If more than 40% of sections are broken, the system uses section-level defaults, never a blind full retry.

## Runtime Simulator

The simulator proves execution awareness by registering routes, rendering pages/components, registering APIs, binding APIs to DB tables, creating DB tables and relationships, loading roles/permissions, checking page permissions, compiling business rules, and verifying premium/admin analytics behavior.

## Failure Handling

Vague prompts become a generic business management app with assumptions. Conflicting prompts are detected and resolved with safer defaults. Incomplete prompts are filled with deterministic domain defaults.

## Deterministic Behavior

The same prompt produces stable output through normalized prompt parsing, stable naming, deterministic templates, sorted roles/permissions, Pydantic validation, and local rule-based generation. `pipeline.deterministic_mode` is always `true`.

## Evaluation Metrics

Latest run:

- Total prompts: `20`
- Success rate: `100%`
- Passed without repair: `10`
- Passed after repair: `10`
- Failed: `0`
- Average latency: about `2.61 ms`
- Average repairs per request: `0.55`
- Repair types observed: `MISSING_PERMISSION`, `MISSING_ROLE`, `PERMISSION_REFERENCES_MISSING_ROLE`, `MISSING_API_ENDPOINT`, `INVALID_FORM_ENDPOINT`, `DB_TABLE_MISSING_PRIMARY_KEY`, `RELATIONSHIP_REFERENCES_MISSING_TABLE`, `PREMIUM_RULE_MISSING`

Reports:

- `outputs/evaluation_report.json`
- `outputs/evaluation_report.md`

## Cost vs Quality Tradeoff

Deterministic generation and validation cost nearly zero locally. LLM usage is optional and should be reserved for richer architecture drafting or domain-specific repair suggestions. Local validation and partial repair avoid full retries and reduce latency/cost.

## Setup

```powershell
cd C:\projects\ConfigAi\configforge-ai
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running Backend

```powershell
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Running Evaluation

```powershell
python backend/run_evaluation.py
```

## API Endpoints

- `GET /`
- `GET /health`
- `POST /generate`
- `POST /generate?inject_fault=true`
- `POST /evaluate`
- `GET /sample-prompts`
- `GET /sample`

## Demo Flow

1. Open `http://127.0.0.1:8000`.
2. Use the default CRM prompt or an example chip.
3. Click **Generate App Config**.
4. Inspect timeline and tabs.
5. Click **Generate With Fault Injection** to show validation catching a controlled fault and repair fixing it.
6. Click **Run Evaluation** to generate metrics.

## Fault Injection Demo

`POST /generate?inject_fault=true` injects one controlled fault immediately before validation. The validator fails, the repair engine applies a localized patch, final validation passes, and execution simulation passes.

Supported controlled faults:

- remove permission -> `MISSING_PERMISSION`
- remove role -> `MISSING_ROLE`
- remove endpoint -> `MISSING_API_ENDPOINT`
- break form endpoint -> `INVALID_FORM_ENDPOINT`
- remove primary key -> `DB_TABLE_MISSING_PRIMARY_KEY`
- remove relationship table -> `RELATIONSHIP_REFERENCES_MISSING_TABLE`
- remove premium rule -> `PREMIUM_RULE_MISSING`

Every repair history entry includes `issue_code`, `location`, `repair`, `strategy: partial_patch`, and `status: fixed`.

## Folder Structure

```text
backend/
  main.py
  run_evaluation.py
  pipeline/
    intent_extractor.py
    system_designer.py
    schema_generator.py
    refinement_layer.py
    validator.py
    repair_engine.py
    runtime_simulator.py
    evaluator.py
    orchestrator.py
  schemas/
    intent_schema.py
    design_schema.py
    app_config_schema.py
    validation_schema.py
    execution_schema.py
  tests/
    product_prompts.json
    edge_case_prompts.json
frontend/
  index.html
outputs/
  generated_configs/
  evaluation_report.json
  evaluation_report.md
```

## Known Limitations

- Deterministic local generation favors reliability over natural-language creativity.
- The runtime simulator validates executable contracts but does not deploy a generated app.
- Optional LLM-assisted generation is not wired by default because no API key should be required.

## Future Improvements

- Add optional OpenAI JSON-mode adapter behind the same validators.
- Add SQLite storage for generated configs and repair traces.
- Add visual architecture graph.
- Add mutation fuzz tests for validator and repair strategies.
- Deploy backend and frontend to a public demo URL.
