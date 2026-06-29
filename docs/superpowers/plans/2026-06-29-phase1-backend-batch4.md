# Phase 1 — Batch 4 Implementation Plan

> Subagent-driven. **Do NOT git commit** unless user requests.

**Goal:** 迁移 W4 资产域首批路由：`local_assets`（优先）+ `asset_library` / `prompt_libraries` 基础 GET。

**Architecture:** 从 `coding/Infinite-Canvas/main.py` 提取本地素材管理逻辑；用户数据目录 `{app_data}/assets/uploads`；资产库/提示词库 JSON 存 `{app_data}/data/`。

---

### Task 8: local_assets (~11 endpoints)

**Endpoints:**
- `POST /api/local-assets/upload`
- `POST /api/local-assets/import-urls`
- `GET /api/local-assets`
- `POST /api/local-assets/folders`
- `PATCH /api/local-assets/folders`
- `PATCH /api/local-assets/items`
- `POST /api/local-assets/delete`
- `POST /api/local-assets/move`
- `POST /api/local-assets/caption`
- `POST /api/local-assets/classify`
- `PATCH /api/local-assets/caption`

**Legacy refs:** main.py ~9214-9817

**New files:**
- `core/paths.py` — `local_upload_dir()`, `asset_library_*`, `prompt_libraries_file()`
- `core/security.py` — `ensure_same_origin_request`
- `core/asset_utils.py` — 分类 JSON 规范化
- `services/asset_ai.py` — caption/classify 上游调用
- `services/local_assets.py`
- `schemas/local_assets.py`
- `routes/local_assets.py`
- `tests/api/test_local_assets.py`

**Notes:**
- 静态文件 `/assets/uploads/*` 由 `app_data/assets` 挂载
- caption/classify 依赖 provider 配置；单测 mock `classify_asset_image_best_effort`

---

### Task 9: asset_library + prompt_libraries basics

**Endpoints (Batch 4 scope):**
- `GET /api/asset-library`
- `GET /api/prompt-libraries`

**New files:**
- `services/asset_library_store.py`
- `services/prompt_library_store.py`
- `routes/asset_libraries.py`

**Deferred (后续 Batch):** POST/PATCH/DELETE 资产库与提示词库 CRUD、shared_folders、workflow upload 等 ~25 路由。

**Do NOT commit.**
