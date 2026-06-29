# Phase 1 — Batch 3 Implementation Plan

> Subagent-driven. **Do NOT git commit** unless user requests.

**Goal:** 迁移 providers/config/models（W5）与 conversations（W3 剩余）。

**Architecture:** 从 `coding/Infinite-Canvas/main.py` 提取 provider 存储、env 读写、上游探测逻辑；对话 CRUD 独立 `services/conversations.py`。

---

### Task 6: Conversations CRUD

**Endpoints:**
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`

**Legacy refs:** main.py ~2992-3060, 12283-12304

**New files:** `services/conversations.py`, `routes/conversations.py`, `schemas/conversation.py`, `tests/api/test_conversations.py`

**Data:** `{app_data_dir()}/data/conversations/{user_id}/*.json`

---

### Task 7: Providers + Config + Models

**Endpoints:**
- `GET /api/config`
- `GET /api/models`
- `GET /api/providers`
- `PUT /api/providers`
- `GET /api/config/token`
- `POST /api/providers/test-connection`
- `POST /api/providers/probe-async`
- `POST /api/providers/fetch-models`
- `GET /api/providers/{provider_id}/fetch-models`

**Legacy refs:** main.py ~620-1310, 2471-2498, 3812+, 7926+, 10159+, 10299-10987

**New files:**
- `core/env_file.py` — load/update `.env`
- `core/provider_constants.py` — defaults, protocol enums
- `services/provider_store.py` — load/save/normalize/public
- `services/provider_probe.py` — test-connection, fetch-models, probe-async
- `schemas/provider.py`
- `routes/providers.py`
- `tests/api/test_providers.py`

**Notes:**
- `runninghub` / `jimeng` 分支需 port 最小可用实现（test-connection 可 mock httpx）
- env 文件路径：`{app_data_dir()}/config/.env`（对齐 design spec §5.3）
- providers JSON：`{app_data_dir()}/data/api_providers.json`
- 静态 runninghub 默认配置可读 `coding/.../static/runninghub/api_providers.json`（若存在）

**Do NOT commit.**
