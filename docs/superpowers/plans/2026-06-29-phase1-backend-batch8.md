# Phase 1 — Batch 8 Implementation Plan

> **Goal:** 完成最后 18 个 legacy HTTP 路由迁移（聊天、画布 AI、角度生成、云端上传、GitHub 更新），达到 ~126 OpenAPI paths。

**Architecture:** 按域拆分 `services/chat.py`、`canvas_llm.py`、`canvas_video.py`、`modelscope_generate.py`、`smart_canvas.py`、`cloud_upload.py`、`app_update.py`；路由注册于 `routes/__init__.py`。

---

## Task 19: Chat (3 endpoints)

- `POST /api/chat` — 同步对话
- `POST /api/chat/stream` — SSE 流式
- `POST /api/chat/agent` — legacy agent parity（非新 Agent 调度）

**Files:** `schemas/chat.py`, `services/chat.py`, `routes/chat.py`

---

## Task 20: Canvas video/LLM + MS generate (3 endpoints)

- `POST /api/canvas-video`
- `POST /api/canvas-llm`
- `POST /api/ms/generate`

**Files:** `schemas/canvas_ai.py`, `services/canvas_video.py`, `canvas_llm.py`, `modelscope_generate.py`, `routes/canvas_ai.py`

---

## Task 21: Angle + smart canvas (3 endpoints)

- `POST /api/angle/poll_status`, `/api/angle/generate`
- `POST /api/smart-canvas/group-export`

**Files:** `routes/angle.py`, `services/smart_canvas.py`, `routes/smart_canvas.py`

---

## Task 22: Misc upload (2 endpoints)

- `POST /api/temp-sh/upload`, `/api/cloud-video/upload`

**Files:** `schemas/upload.py`, `services/cloud_upload.py`, `routes/upload.py`

---

## Task 23: GitHub update (6 endpoints)

- `GET /api/update-connectivity/probe`, `/api/update-connectivity`
- `GET /api/check-update`
- `POST /api/update-from-github`
- `GET /api/update-backups`
- `POST /api/update-rollback`

**Files:** `schemas/update.py`, `services/app_update.py`, `routes/update.py`

---

## Wiring

- `routes/__init__.py` — 注册 chat、canvas_ai、angle、smart_canvas、upload、update routers

---

## Tests

- `tests/api/test_chat.py`
- `tests/api/test_canvas_ai.py`
- `tests/api/test_angle.py`
- `tests/api/test_update.py`

```bash
uv run pytest tests/api -v
uv run python scripts/export_openapi_baseline.py
```

---

## Verification

- [x] `uv run pytest tests/api -v` 全绿
- [x] OpenAPI paths ~126（含 `/generate` 云端 Z-Image）
- [x] `CONTEXT.md` §1/§3 更新
