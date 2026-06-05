# Loom Video Script

## 1. Problem

ConfigForge AI solves a reliability problem in AI software generation. A prompt can describe an app, but real software needs consistent UI, API, database, auth, permissions, business logic, validation, repair, and runtime behavior.

## 2. Why Single-Prompt Generation Fails

A single prompt can produce JSON that looks convincing but is not executable. Forms may submit to missing APIs, APIs may write fields that do not exist in tables, admin pages may forget permissions, payments may lack billing rules, and premium pages may ship without gating.

## 3. Why This Is Compiler-Style

This project treats natural language as source code. It compiles the request through intermediate representations: intent, design, strict schema, refinement, validation, repair, runtime simulation, and final executable app config.

## 4. Stage 1: Intent Extraction

The intent extractor parses app type, domain, goal, features, entities, roles, auth requirements, payments, analytics, premium behavior, CRUD needs, ambiguities, conflicts, and missing details. Vague prompts are handled with assumptions, not failure.

## 5. Stage 2: System Design

The system designer creates a config-driven full-stack architecture. It defines modules, entities, roles, user flows, access model, data model summary, business-rule summary, and risk notes.

## 6. Stage 3: Schema Generation

The schema generator creates UI pages, routes, layouts, components, forms, submit endpoints, APIs, DB tables, relationships, auth roles, granular permissions, and business logic.

## 7. Stage 4: Refinement

The refinement layer deduplicates routes, endpoints, tables, and entities. It also normalizes missing permission definitions before strict validation.

## 8. Validation Engine

The validator checks UI-to-API, API-to-DB, DB primary keys, relationships, roles, permissions, admin analytics, payment permissions, premium gating, duplicate surfaces, plain password storage, login/users coupling, and business-rule coverage.

## 9. Repair Engine

The repair engine is localized. It does not regenerate everything. It adds missing tables, primary keys, endpoints, roles, permissions, business rules, or columns only where needed. Every repair is recorded with issue code, location, before/after summary, strategy, and status.

## 10. Fault Injection Demo

Click **Generate With Fault Injection** or call `POST /generate?inject_fault=true`. The system injects a controlled fault, such as removing a permission, role, endpoint, primary key, relationship table, or premium rule. Validation fails first, the repair history records the localized fix, final validation passes, and execution simulation passes.

## 11. Runtime Simulator

The simulator registers routes, renders pages and components, registers endpoints, binds APIs to tables, creates DB tables and relationships, loads roles and permissions, checks access, compiles business rules, and verifies premium/admin analytics behavior.

## 12. Evaluation Framework

The evaluator runs 20 prompts: 10 real product prompts and 10 edge cases. It saves `evaluation_report.json` and `evaluation_report.md`.

## 13. Metrics

Latest metrics: 20 prompts, 100% success rate, 10 passed without repair, 10 passed after repair, 0 failed, and average latency around 2.61 ms. The report demonstrates multiple repair types including missing permissions, missing roles, missing endpoints, invalid form endpoints, missing primary keys, missing relationship tables, and missing premium rules.

## 14. Cost vs Quality Tradeoff

The default engine is deterministic and local, so cost is near zero. LLMs can be added optionally for richer generation, but validation, repair, and runtime simulation remain deterministic. Partial repair saves cost by avoiding full retries.

## 15. Why This Can Power a Real Product

ConfigForge AI creates a durable contract between UI, API, database, auth, and business logic. That contract can feed app builders, internal tools, code generators, or deployment pipelines while preserving traceability and reliability.
