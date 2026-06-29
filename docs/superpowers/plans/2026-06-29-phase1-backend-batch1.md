# Phase 1 — 后端 Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development. One task per subagent; update CONTEXT.md §3 after each task. **Do NOT git commit** unless user explicitly requests.

**Goal:** 建立 legacy OpenAPI 全量 baseline，并迁移第一批低耦合 API（queue + history）。

**Architecture:** 从 `coding/Infinite-Canvas/main.py` 导出 baseline；新代码在 `services/api/src/infinite_canvas/` 按 routes/services 拆分；pytest parity 对照。

**Tech Stack:** uv · FastAPI · pytest · httpx

---

### Task 1: Legacy OpenAPI baseline

**Files:**
- Create: `scripts/export_legacy_openapi.py`
- Create: `tests/fixtures/openapi_legacy_baseline.json` (generated)
- Create: `tests/api/test_openapi_baseline.py`
- Modify: `CONTEXT.md` §3

**Requirements:**
1. Script adds `coding/Infinite-Canvas` to sys.path, imports `app` from `main`, calls `app.openapi()`, writes `tests/fixtures/openapi_legacy_baseline.json`
2. Handle import errors gracefully with clear message if coding/ missing
3. Test asserts current `create_app().openapi()` path count <= legacy (Phase 0 subset) OR test that legacy fixture file exists and has >100 paths
4. Run `uv run pytest tests/api/test_openapi_baseline.py -v`
5. Append CONTEXT.md log entry

**Do NOT commit.**

---

### Task 2: Queue + History routes

**Files:**
- Create: `services/api/src/infinite_canvas/services/history.py` (extract logic from legacy)
- Create: `services/api/src/infinite_canvas/routes/history.py`
- Modify: `services/api/src/infinite_canvas/routes/__init__.py`
- Modify: `services/api/src/infinite_canvas/app.py` (include router)
- Create: `tests/api/test_history.py`
- Modify: `CONTEXT.md` §3

**Endpoints to migrate (parity with coding/Infinite-Canvas/main.py):**
- `GET /api/queue_status`
- `GET /api/history`
- `POST /api/history/delete`

**Requirements:**
1. Read legacy handlers in main.py (~13816-13849) and extract behavior
2. Use `app_data_dir()` paths where legacy uses BASE_DIR for history.json / queue
3. pytest covers queue_status shape, history list, delete
4. `uv run pytest tests/api -v` all pass
5. Append CONTEXT.md log entry

**Do NOT commit.**

---

### Task 3: WebSocket `/ws/stats`

**Files:**
- Create: `services/api/src/infinite_canvas/core/websocket.py`
- Modify: `services/api/src/infinite_canvas/app.py`
- Create: `tests/api/test_websocket.py` (minimal connect test)

**Requirements:** Port ConnectionManager from legacy main.py lines ~77-173; register websocket route; ping/pong behavior preserved.

**Do NOT commit.**
