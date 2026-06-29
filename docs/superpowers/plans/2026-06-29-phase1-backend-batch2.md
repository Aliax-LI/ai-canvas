# Phase 1 — Batch 2 Implementation Plan

> Subagent-driven. **Do NOT git commit** unless user requests.

**Goal:** 迁移 upload/media 与 canvases/projects CRUD。

---

### Task 4: Media + Upload routes

**Endpoints:**
- `GET /api/media-preview`
- `GET /api/image-jpeg`
- `GET /api/view`
- `GET /api/download-output`
- `POST /api/upload`

**Legacy refs:** main.py ~4761-4832, 9010-9106; helpers for PIL preview, output paths, ComfyUI proxy.

**New files:** `core/media.py`, `core/comfyui.py` (optional), `services/media.py`, `routes/media.py`, `tests/api/test_media.py`

---

### Task 5: Canvases + Projects

**Endpoints:**
- Projects: GET/POST `/api/projects`, POST/DELETE `/api/projects/{id}`
- Canvases: all `/api/canvases*` routes (11 endpoints)

**Legacy refs:** main.py ~3077-3240, 12308-13535

**New files:** `services/canvas_store.py`, `services/projects.py`, `schemas/canvas.py`, `routes/canvases.py`, `tests/api/test_canvases.py`

**Data:** `{app_data_dir()}/data/canvases/`, `projects.json`; fallback read from coding root for dev.

---

### Task 6 (optional batch 2b): `/api/ai/upload` + canvas-assets index

Defer if Task 4-5 too large.
