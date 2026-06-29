# Phase 0 — 迁移脚手架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仓库根目录建立 uv monorepo 骨架，启动可运行的 FastAPI 服务，挂载上游 `coding/Infinite-Canvas/static`，为后续 147 API 拆分提供基线与测试夹具。

**Architecture:** `services/api/src/infinite_canvas/` 包 + `create_app()` 工厂；静态资源运行时从 gitignore 的 `coding/Infinite-Canvas/` 读取；用户数据目录通过 `core/paths.py` 解析；Phase 0 不拆 `main.py` 业务，仅 health + 静态页 + OpenAPI baseline 脚本。

**Tech Stack:** uv · Python 3.10+ · FastAPI · uvicorn · pytest · httpx

**后续计划:** Phase 1 起按 `docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md` §5.2 逐域拆分 routes；Phase 4 起 `apps/web` React；Phase 8 Tauri。

---

## 文件结构（Phase 0 创建）

```
ai-canvas/
├── pyproject.toml
├── uv.lock
├── services/api/src/infinite_canvas/
│   ├── __init__.py
│   ├── main.py              # CLI 入口
│   ├── app.py               # create_app()
│   └── core/
│       ├── __init__.py
│       ├── config.py        # Settings
│       └── paths.py         # REPO_ROOT, CODING_ROOT, APP_DATA
├── services/api/src/infinite_canvas/routes/
│   ├── __init__.py
│   └── system.py            # /api/app-info, /health
├── tests/
│   ├── conftest.py
│   └── api/
│       └── test_system.py
├── scripts/
│   └── export_openapi_baseline.py
└── workflows/               # 从 coding 复制或运行时引用
```

---

### Task 1: uv 项目与包结构

**Files:**
- Create: `pyproject.toml`
- Create: `services/api/src/infinite_canvas/__init__.py`
- Create: `services/api/src/infinite_canvas/core/__init__.py`
- Create: `services/api/src/infinite_canvas/routes/__init__.py`

- [ ] **Step 1:** 写入 `pyproject.toml`（hatchling 构建，`packages = ["services/api/src/infinite_canvas"]`）

- [ ] **Step 2:** 运行 `uv sync`

- [ ] **Step 3:** 验证 `uv run python -c "import infinite_canvas"`

---

### Task 2: paths 与 config

**Files:**
- Create: `services/api/src/infinite_canvas/core/paths.py`
- Create: `services/api/src/infinite_canvas/core/config.py`

- [ ] **Step 1:** `paths.py` 解析 `REPO_ROOT`、`CODING_ROOT`、`legacy_static_dir()`、`app_data_dir()`

- [ ] **Step 2:** `config.py` 提供 `Settings`：`host`, `port`, `data_dir`, `coding_root`

- [ ] **Step 3:** 单元测试 `tests/api/test_paths.py`（可选 Phase 0 简化为 test_system 覆盖）

---

### Task 3: FastAPI 应用壳

**Files:**
- Create: `services/api/src/infinite_canvas/app.py`
- Create: `services/api/src/infinite_canvas/routes/system.py`
- Create: `services/api/src/infinite_canvas/main.py`

- [ ] **Step 1:** `create_app()` 注册 system 路由

- [ ] **Step 2:** 若 `legacy_static_dir()` 存在，mount `/static`、`/assets`、`/output`（来自 coding 对应目录）

- [ ] **Step 3:** `GET /` 返回 `index.html`（legacy static）

- [ ] **Step 4:** CLI: `uv run infinite-canvas --port 3000`

---

### Task 4: 测试与 OpenAPI baseline

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/api/test_system.py`
- Create: `scripts/export_openapi_baseline.py`

- [ ] **Step 1:** pytest `test_health`, `test_app_info`

- [ ] **Step 2:** 若 coding 服务可运行，脚本导出 `tests/fixtures/openapi_baseline.json`

- [ ] **Step 3:** `uv run pytest tests/api -v` 全绿

---

### Task 5: 文档更新

**Files:**
- Modify: `CONTEXT.md` §1 阶段 → M1 进行中；§3 追加日志

- [ ] **Step 1:** 更新 CONTEXT.md

---

## Spec 覆盖（Phase 0）

| 规格要求 | 本 Phase |
|----------|----------|
| uv monorepo | ✅ Task 1 |
| 目录 `services/api` | ✅ |
| 用户数据目录抽象 | ✅ Task 2 |
| legacy static 可访问 | ✅ Task 3 |
| OpenAPI baseline | ✅ Task 4 |
| 147 API 拆分 | ⏭ Phase 1+ |
| React / Tauri | ⏭ Phase 4+ / 8 |

---

## 验收标准（Phase 0 Done）

1. `uv sync && uv run infinite-canvas` 启动无报错
2. `curl http://127.0.0.1:3000/api/app-info` 返回 JSON
3. 浏览器打开 `/` 可见上游 Studio 首页（需本地存在 `coding/Infinite-Canvas/static`）
4. `uv run pytest tests/api -v` 通过
