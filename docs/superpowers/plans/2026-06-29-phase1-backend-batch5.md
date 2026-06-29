# Phase 1 — Batch 5 Implementation Plan

> **Goal:** 完成 ComfyUI 域：instances、workflows CRUD/run、generate、canvas-comfy-tasks、upload-base64、image-params。

**Architecture:** 工作流存 `{app_data}/workflows/`（`custom/` 子目录）；内置工作流回退 `coding/Infinite-Canvas/workflows/`。生成逻辑复用 `core/queue.py`、`core/websocket.py`、`services/history.py`。

---

## Task 13: ComfyUI instances + workflows (~8 endpoints)

**Endpoints:**
- `GET/PUT /api/comfyui/instances`
- `GET /api/workflows`, `GET /api/workflows/{name:path}`
- `POST /api/workflows`, `PUT /api/workflows/{name:path}/config`, `DELETE /api/workflows/{name:path}`
- `POST /api/workflows/{name:path}/run`

**Files:**
- `core/paths.py` — `workflows_dir()`, `legacy_workflows_dir()`
- `services/comfyui_workflows.py`
- `routes/comfyui.py`
- `schemas/comfyui.py`

**Legacy refs:** main.py ~14887-15025, ~14506-14519

---

## Task 14: POST /api/generate + canvas-comfy-tasks

**Endpoints:**
- `POST /api/generate`
- `POST /api/canvas-comfy-tasks`, `GET /api/canvas-comfy-tasks/{task_id}`

**Files:**
- `services/comfyui_generate.py` — queue、backend 选择、ComfyUI /prompt、history 轮询、输出下载、history 写入、WS 广播

**Legacy refs:** main.py ~14252-14500, ~11186-11236

---

## Task 15: ComfyUI upload + image-params

**Endpoints:**
- `POST /api/comfyui/upload-base64`
- `GET /api/image-params`

**Legacy refs:** main.py ~9184, ~11254-11307

---

## Wiring

- `routes/__init__.py` — `comfyui_router`
- `core/comfyui.py` — `save_instances()`, load balancing
- `core/env_file.update_env_values` — `COMFYUI_INSTANCES`
- `app.py` startup — `set_global_loop` for WS broadcast from sync generate

---

## Tests

- `tests/api/test_comfyui.py` — instances、workflows list/upload、upload-base64 mock、image-params
- `tests/api/test_generate.py` — mocked ComfyUI prompt/history/download

---

## Verification

```bash
uv run pytest tests/api -v
uv run python scripts/export_openapi_baseline.py
```

**Batch 5 完成后：** OpenAPI paths 增加 ~14；pytest 全绿。
