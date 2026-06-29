# Phase 1 — Batch 6 Implementation Plan

> **Goal:** 完成 RunningHub（12 端点）与即梦 Jimeng（8 端点）迁移，保持 API JSON parity。

**Architecture:** RunningHub 业务逻辑在 `services/runninghub.py`，工作流本地存储 `data/runninghub_workflows.json`；Jimeng 复用 CLI subprocess（macOS/Linux 原生、Windows WSL 分支）。

---

## Task 16: RunningHub (~12 endpoints)

**Endpoints:**
- `GET /api/runninghub/app-info`
- `POST /api/runninghub/submit`
- `POST /api/runninghub/workflow-submit`
- `GET /api/runninghub/workflow-info`
- `GET /api/runninghub/workflows`
- `GET /api/runninghub/workflows/{workflow_id}`
- `POST /api/runninghub/workflows/fetch`
- `PUT /api/runninghub/workflows/{workflow_id}`
- `DELETE /api/runninghub/workflows/{workflow_id}`
- `GET /api/runninghub/query`
- `POST /api/runninghub/upload-asset`

**Files:**
- `core/paths.py` — `runninghub_workflow_store_file()`
- `services/runninghub.py`
- `routes/runninghub.py`
- `schemas/runninghub.py`

**Legacy refs:** main.py ~9839-10156, helpers ~7567-8306, ~14521-14882

---

## Task 17: Jimeng (~8 endpoints)

**Endpoints:**
- `GET /api/jimeng/status`
- `GET /api/jimeng/credit`
- `POST /api/jimeng/logout`
- `POST /api/jimeng/login/start`
- `GET /api/jimeng/login/status`
- `POST /api/jimeng/help`
- `POST /api/jimeng/query-media`

**Files:**
- `services/jimeng.py` — CLI、登录会话、query-media、JimengPendingError
- `routes/jimeng.py`
- `schemas/jimeng.py`
- `app.py` — JimengPendingError → 202 handler

**Legacy refs:** main.py ~10158-10297, jimeng helpers ~3868-4422

---

## Wiring

- `routes/__init__.py` — register `runninghub_router`, `jimeng_router`
- `services/provider_probe.py` — `jimeng_status` 改从 `services.jimeng` 导入

---

## Tests

- `tests/api/test_runninghub.py` — mock httpx app-info、workflows list
- `tests/api/test_jimeng.py` — mock CLI 未安装 / 已登录 status

```bash
uv run pytest tests/api -v
uv run python scripts/export_openapi_baseline.py
```

---

## Verification

- [ ] `uv run pytest tests/api -v` 全绿
- [ ] OpenAPI paths ~95（77 + 20）
- [ ] `CONTEXT.md` §1/§3 更新
