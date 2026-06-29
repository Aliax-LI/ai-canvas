# Phase 1 — Batch 4b Implementation Plan

> **Goal:** 完成资产域 CRUD：`prompt_libraries`（10）、`asset_library`（~15，avatar 501）、`shared_folders`（6）。

**Architecture:** 延续 Batch 4 的 JSON 存储与 `{app_data}` 路径约定；共享文件夹登记根目录为 `app_data_dir()`（桌面数据根），非 `coding/`。

---

## Task 10: prompt_libraries CRUD (10 endpoints)

**Endpoints:**
- `POST /api/prompt-libraries`
- `PATCH /api/prompt-libraries/{library_id}`
- `DELETE /api/prompt-libraries/{library_id}`
- `POST /api/prompt-libraries/items`
- `PATCH /api/prompt-libraries/items/{item_id}`
- `DELETE /api/prompt-libraries/items/{item_id}`
- `POST /api/prompt-libraries/items/delete`
- `POST /api/prompt-libraries/categories`
- `PATCH /api/prompt-libraries/categories/{category_id}`
- `DELETE /api/prompt-libraries/categories/{category_id}`

**Files:**
- `services/prompt_library_store.py` — `find_prompt_library`
- `routes/prompt_libraries.py`
- `schemas/asset_libraries.py`
- `tests/api/test_prompt_library_crud.py`

**Legacy refs:** main.py ~12766-12943, ~5722

---

## Task 11: asset_library CRUD (~15 endpoints)

**Endpoints:** libraries/categories/items CRUD、batch、classify、move、crop；`register-avatar` / `avatar-status` → **501 尚未迁移**

**Files:**
- `services/asset_library_store.py` — `find_*`, `make_asset_library_item`, `remove_asset_library_file`, `unique_asset_category_dir`, `asset_library_media_kind`
- `routes/asset_libraries.py`（扩展）
- `tests/api/test_asset_library_crud.py`

**Deps:** `core/output_files.output_file_from_url`, `services/asset_ai.classify_asset_image_best_effort`

**Legacy refs:** main.py ~5047-5118, ~5384-5414, ~12945-13492

**Deferred:** `POST /api/asset-library/workflows/upload`

---

## Task 12: shared_folders (6 endpoints)

**Endpoints:**
- `GET/POST /api/shared-folders`
- `DELETE /api/shared-folders/{folder_id}`
- `GET /api/shared-folders/{folder_id}/tree`
- `GET /api/shared-folders/{folder_id}/file`
- `POST /api/shared-folders/import`

**Files:**
- `core/paths.py` — `shared_folders_file()`
- `services/shared_folders_store.py`
- `routes/shared_folders.py`
- `tests/api/test_shared_folders.py`

**Note:** `shared_resolve_register` 校验路径须在 `app_data_dir()` 内。

**Legacy refs:** main.py ~5416-5548, ~13078-13179

---

## Wiring

- `routes/__init__.py` — `prompt_libraries_router`, `shared_folders_router`
- `/assets/library/*` 由既有 `app_assets_dir()` 挂载覆盖

---

## Verification

```bash
uv run pytest tests/api -v
uv run python scripts/export_openapi_baseline.py
```

**Batch 4b 完成后：** ~67 OpenAPI paths，pytest 62 passed。
