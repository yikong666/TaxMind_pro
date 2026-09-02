# Workbench Conversation and Sample Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete governed workbench conversations and verify a small, approved official-data path end to end.

**Architecture:** MySQL remains authoritative for conversations, messages, run records and audit. SSE only transports persisted run events; it never exposes private reasoning. External data is downloaded only from an approved manifest and remains separate from browser upload.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, Alembic, React, TypeScript, TanStack Query, SSE, pytest, Vitest.

**Spec:** User-approved five-step scope in this conversation.

## Global Constraints

- Use official public sources only; do not bypass login, CAPTCHA, signatures or anti-bot controls.
- Retain audit, tenant, source, snapshot and deterministic-rule boundaries.
- Never present synthetic model answers, streamed content or downloaded data as verified results.
- No commit or push without a new explicit user instruction.

---

### Task 1: Conversation lifecycle

**Files:** conversation domain/service/repository/router, Alembic migration, web conversation client/workspace, backend and web tests.

- [x] Write failing tests for owner-authorized soft delete/restore, deleted-conversation read rejection, audit events, and UI confirmations.
- [x] Add a `deleted_at`/status transition with org-scoped lookup; preserve messages and audit history and allow an authorized restore transition.
- [x] Add `DELETE /api/v1/conversations/{id}` and `POST /api/v1/conversations/{id}/restore` returning governed status responses; regenerate OpenAPI and add client/UI invalidation.
- [x] Run focused pytest, Vitest, typecheck, lint and browser verification.

### Task 2: Persisted model runs and final answers

**Files:** query-run domain/service/repository/router and migrations; conversation message persistence; frontend run client/workspace; tests.

- [x] Write failing tests proving a run records facts, evidence IDs, rule version IDs, knowledge snapshot and final-answer message atomically without private reasoning.
- [x] Add explicit run states `queued`, `running`, `completed`, `failed`, `needs_input`; persist only safe answer text and citation references.
- [x] Expose authenticated run create/read APIs and render authoritative status, citations, gaps and errors in the workspace.
- [x] Run focused backend/frontend validation and browser checks.

### Task 3: SSE event contract

**Files:** run event contract/router/service, frontend stream client/workspace, tests.

- [x] Write contract/unit tests for `started`, `delta`, `completed`, failed/needs-input state, reconnect cursor and malformed cursor rejection. Authentication remains enforced by the shared bearer dependency before stream access.
- [x] Emit only persisted safe deltas and terminal records keyed by `run_id`; do not send hidden prompts, secrets or chain of thought.
- [x] Add bearer-header fetch stream lifecycle, replay cursor, reconnect polling and final REST reconciliation. Native `EventSource` is intentionally not used because it cannot supply the required Authorization header without exposing a token in the URL.
- [x] Run SSE unit/contract tests and preview-browser regression. Live disconnect/retry against the API remains dependent on the local Docker MySQL service being reachable.

### Task 4: Approved official-data sample

**Files:** `data/manifests/` approved manifest, download/import/verification scripts, runbook, tests.

- [x] Present 3–5 exact official URLs, title/authority/region/type and expected file format to the user; stop for confirmation before network download.
- [x] Download at low frequency, recording URL, timestamp, SHA-256, status and failure reason; never include credentials. Three confirmed files succeeded; the confirmed Shenzhen URL failed TLS verification and was not substituted or imported.
- [x] Import only successfully verified files through governed source/document workflows. Three sources and draft documents were created in an isolated MySQL/MinIO acceptance environment; the failed Shenzhen source was not imported.
- [ ] Verify policy status/date/region filtering and record actual outputs.

### Task 5: End-to-end acceptance

**Files:** E2E tests, `docs/runbooks/`, `docs/CHANGELOG.md`.

- [ ] Execute a fictional case through conversation, run, citations, review, sample-data retrieval and safe failure paths.
- [ ] Run backend ruff/format/mypy/pytest, frontend lint/typecheck/Vitest/build and browser E2E.
- [ ] Review diff and report verified, unverified and deferred capabilities separately.
