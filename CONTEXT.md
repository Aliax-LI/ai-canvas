# CONTEXT — 项目方向与实现记录

> **Agent 必读**：每次会话开始先读本文 **§1 方向锚点** 与 **§3 最新记录**；完成代码变更后必须追加 **§3 更新日志**，防止实现偏离整体目标。  
> 稳定背景与设计细节见 [`docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md`](docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md)。协作规则见 [`AGENTS.md`](AGENTS.md)。**视觉规范见 [`DESIGN.md`](DESIGN.md)。**

---

## 1. 方向锚点（勿偏离）

| 项 | 锁定内容 |
|----|----------|
| 目标 | Infinite-Canvas **全量迁移** + **现代化 UI** + **Tauri 2 桌面**（Win/macOS） |
| v1 范围 | **strict parity**（147 API + 14 页 + 全部画布能力）；**不**做 Agent 调度画布 |
| 仓库根 | `ai-canvas/`，新代码在 `apps/`、`services/`、`packages/`、`tests/` |
| 上游对照 | `coding/Infinite-Canvas/`（**gitignore**，只读，不提交） |
| 技术栈 | uv · FastAPI · React · shadcn/ui · Tauri 2 · `@xyflow/react` |
| 视觉规范 | **`DESIGN.md`**（Token、B+ 双模式、画布节点） |
| 数据目录 | 用户数据与代码分离 → `~/.infinite-canvas/` |
| 发布门槛 | parity 测试全绿后才发桌面安装包 |

**当前阶段**：`M1 — 后端 Batch 2 完成`（Phase 0 脚手架 + Batch 1 history/ws + Batch 2 media/upload/canvases/projects，OpenAPI baseline **20 paths**）

**当前里程碑进度**：

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0 基线 / 文档 | ✅ 完成 | `.gitignore`、`AGENTS.md`、`CONTEXT.md`、`DESIGN.md`、设计规格 |
| M1 uv 后端壳 | ✅ 完成 | `pyproject.toml`、`infinite_canvas` 包、health/app-info、static 挂载 |
| M2–M3 后端 100% parity | 🟡 进行中 | 已迁移 ~20/147 路由（history、ws、media、canvases/projects）；pytest **33 passed** |
| M4–M7 前端 React | ⚪ 未开始 | 14 页 + 双画布 |
| M8–M9 Tauri 双端 | ⚪ 未开始 | Win/macOS 安装包 |

---

## 2. 实现范围速查（迁移清单）

<details>
<summary>点击展开：后端 / 前端 / 集成（与 design spec 一致）</summary>

### 后端（147 HTTP + `/ws/stats`）

- 源：`coding/Infinite-Canvas/main.py`（~15k 行）→ 目标：`services/api/src/infinite_canvas/`

### 前端（14 页 → React）

| 原 HTML | 计划路由 | 迁移状态 |
|---------|----------|----------|
| index.html | `/` | ⚪ |
| canvas-list.html | `/canvases` | ⚪ |
| canvas.html | `/canvas/:id` | ⚪ |
| smart-canvas.html | `/smart/:id` | ⚪ |
| asset-manager.html | `/assets` | ⚪ |
| api-settings.html | `/settings/api` | ⚪ |
| comfyui-settings.html | `/settings/comfyui` | ⚪ |
| gpt-chat.html | `/chat` | ⚪ |
| zimage / enhance / klein / online / angle | `/tools/*` | ⚪ |

### 外部集成（v1 保持行为）

ComfyUI · API/APIMart · ModelScope · RunningHub · 火山 · 即梦 CLI · PS/Chrome 插件（localhost）

</details>

---

## 3. 更新日志（按时间倒序）

> Agent：**每次**完成有意义的代码/配置变更后，在**本表最上方**插入一条。  
> 格式：`### YYYY-MM-DD — 简短标题` + 变更摘要 + 影响范围 + 下一步。

---

### 2026-06-29 — Phase 1 Task 5：Canvases + Projects CRUD 迁移

**变更摘要**

- 新增 `services/canvas_store.py`：画布 CRUD、回收站（delete/restore/purge）、meta/touch、乐观锁 PUT、legacy `coding/` 画布目录只读回退
- 新增 `services/projects.py`：项目列表/创建/更新/删除，默认项目保护，删除时画布迁回 default
- 新增 `schemas/canvas.py`、`routes/canvases.py`（11 画布 + 4 项目端点）
- 新增 `tests/api/test_canvases.py`（9 条）

**影响范围**

- `services/api/src/infinite_canvas/`（schemas、services、routes、core/paths.py）
- `tests/api/test_canvases.py`、`tests/fixtures/openapi_baseline.json`
- `CONTEXT.md`

**验证**

- [x] `uv run pytest tests/api -v` 33 passed

**下一步**

- Phase 1 后续：assets/providers/comfyui 等域迁移

**方向对齐**：✅ JSON 形状与 legacy 一致；数据目录 `{app_data_dir()}/data/canvases/` + `projects.json`；未改 `coding/`

---

### 2026-06-29 — Phase 1 Task 4：Media + Upload 路由迁移

**变更摘要**

- 新增 `core/media.py`（PIL 预览/JPEG 缓存、content-type、本地路径解析）与 `core/comfyui.py`（`COMFYUI_INSTANCES` 环境变量）
- 新增 `services/media.py`、`routes/media.py`：`GET /api/media-preview`、`/api/image-jpeg`、`/api/view`、`/api/download-output`、`POST /api/upload`
- 扩展 `core/paths.py`（`media_preview_dir`、assets input/output）、`core/config.py`（comfyui_instances 默认）
- 新增 `tests/api/test_media.py`（9 条）

**影响范围**

- `services/api/src/infinite_canvas/core/`、`services/`、`routes/`
- `tests/api/test_media.py`、`tests/fixtures/openapi_baseline.json`
- `CONTEXT.md`

**验证**

- [x] `uv run pytest tests/api -v` 33 passed

**下一步**

- Task 5 canvases/projects（同批 Batch 2）

**方向对齐**：✅ 预览缓存目录 `{app_data_dir()}/data/media_previews`；ComfyUI 代理与 legacy 行为一致；未改 `coding/`

---

### 2026-06-29 — Cursor 项目 Hook：自动提醒 CONTEXT.md 更新

**变更摘要**

- 新增 `.cursor/hooks.json`：在 `stop` 与 `subagentStop` 事件调用 `update-context-on-stop.sh`（`loop_limit: 1`）
- 新增 `.cursor/hooks/update-context-on-stop.sh`：检测有意义代码变更且 `CONTEXT.md` 未同步时，输出 `followup_message` 要求 Agent 补写 §3 日志
- 更新 `AGENTS.md` §2.0：说明 Hook 行为与 Agent 必须响应 follow-up 的义务

**影响范围**

- `.cursor/hooks.json`、`.cursor/hooks/update-context-on-stop.sh`（新建）
- `AGENTS.md`、`CONTEXT.md`

**验证**

- [x] `echo '{}' | .cursor/hooks/update-context-on-stop.sh` 输出 `{}` 且 exit 0
- [ ] Cursor Hooks 设置页可见项目 Hook（需重启 Cursor 后确认）

**下一步**

- 继续 Phase 1 后端路由迁移

**方向对齐**：✅ 强化 CONTEXT 维护纪律，不改变 v1 功能 scope

---

### 2026-06-29 — Phase 1 Task 3：WebSocket `/ws/stats` 迁移

**变更摘要**

- 新增 `core/websocket.py`：移植 legacy `ConnectionManager`（connect/disconnect、broadcast_count、online_count、new_image/canvas/asset 广播、personal message）
- 在 `app.py` 注册 `@app.websocket("/ws/stats")`，支持 `client_id` 查询参数与 `ping`/`pong` 文本消息
- 新增 `tests/api/test_websocket.py`（3 条：连接 stats、ping/pong、canvas_ 客户端不计入 online_count）

**影响范围**

- `services/api/src/infinite_canvas/core/websocket.py`（新建）
- `services/api/src/infinite_canvas/app.py`
- `tests/api/test_websocket.py`（新建）
- `CONTEXT.md`

**验证**

- [x] `uv run pytest tests/api -v` 15 passed

**下一步**

- Phase 1 后续任务：继续按设计规格 §5.2 迁移下一批 routes

**方向对齐**：✅ WebSocket 消息格式与 legacy 一致，PS 插件兼容；未改 `coding/`；未扩 v1 scope

---

### 2026-06-29 — Phase 1 Task 2：Queue + History 路由迁移

**变更摘要**

- 新增 `services/history.py`：`GET /api/history`、 `POST /api/history/delete` 业务逻辑；历史文件优先 `{app_data_dir()}/history.json`，只读回退 `coding/Infinite-Canvas/history.json`
- 新增 `core/queue.py`（内存队列）与 `core/output_files.py`（删除历史时解析 `/output`、`/assets` URL）
- 新增 `routes/history.py` 薄路由层，含 `GET /api/queue_status`
- 新增 `tests/api/test_history.py`（6 条）；更新 `tests/fixtures/openapi_baseline.json`（6 paths）

**影响范围**

- `services/api/src/infinite_canvas/`（core、services、routes）
- `tests/api/test_history.py`、`tests/fixtures/openapi_baseline.json`
- `CONTEXT.md`

**验证**

- [x] `uv run pytest tests/api -v` 12 passed

**下一步**

- Phase 1 后续任务：继续按设计规格 §5.2 迁移下一批 routes

**方向对齐**：✅ 3 个 legacy 端点 JSON 形态与状态码对齐；未改 `coding/`；未扩 v1 scope

---

### 2026-06-29 — Phase 1 Task 1：Legacy OpenAPI baseline

**变更摘要**

- 新增 `scripts/export_legacy_openapi.py`：从 `coding/Infinite-Canvas/main.py` 导出 `app.openapi()`
- 生成 `tests/fixtures/openapi_legacy_baseline.json`（123 paths）
- 新增 `tests/api/test_openapi_baseline.py`：legacy 存在性、路由数量、Phase 0 为 legacy 子集（`/health` 为 scaffold 新增）

**影响范围**

- `scripts/`、`tests/fixtures/`、`tests/api/`、`CONTEXT.md`

**验证**

- [x] `uv run python scripts/export_legacy_openapi.py` 成功（123 paths）
- [x] `uv run pytest tests/api -v` 6 passed

**下一步**

- Phase 1 后续：按设计规格 §5.2 拆分第一批 routes（upload、canvases）

**方向对齐**：✅ 建立 legacy OpenAPI 对照基线；未改 `coding/`；未扩 v1 scope

---

### 2026-06-29 — Phase 0 脚手架（M1 启动）

**变更摘要**

- 新增 `pyproject.toml` + `uv.lock`：uv 工程、`infinite-canvas` CLI
- 新增 `services/api/src/infinite_canvas/`：`app.py`、`core/paths.py`、`core/config.py`、`routes/system.py`
- 挂载 `coding/Infinite-Canvas/static|assets|output`（本地存在时）；`GET /` → legacy `index.html`
- 新增 `tests/api/test_system.py`（2 passed）、`scripts/export_openapi_baseline.py`
- 新增实现计划 `docs/superpowers/plans/2026-06-29-phase0-migration-scaffold.md`

**影响范围**

- `services/api/`、`tests/`、`scripts/`、`pyproject.toml`、`.venv`

**验证**

- [x] `uv sync` 成功
- [x] `uv run pytest tests/api -v` 2 passed
- [x] `uv run infinite-canvas --port 3001` + `/health`、`/api/app-info`、`/` 200

**下一步**

- Phase 1：从 `coding/Infinite-Canvas/main.py` 导出完整 OpenAPI baseline（对照旧服务）
- 按设计规格 §5.2 拆分第一批 routes（upload、canvases、health 扩展）

**方向对齐**：✅ Phase 0 绞杀者第一步；未改 API 契约；未做 React/Tauri

---

### 2026-06-29 — 视觉规范 DESIGN.md

**变更摘要**

- 新增 `DESIGN.md`：Token（light/dark）、B+ 双模式布局、字体、shadcn 组件、画布/智能画布节点、动效、Tauri chrome、无障碍与禁止项
- `CONTEXT.md`、`AGENTS.md` 增加对 `DESIGN.md` 的引用

**影响范围**

- 文档；`apps/web` 实现 UI 时以 `DESIGN.md` 为唯一视觉准绳

**验证**

- [x] Token 与 shadcn 变量命名对齐
- [ ] `apps/web/src/styles/tokens.css` 落地（待 M4）

**下一步**

- Phase 0 脚手架；M4 时按 `DESIGN.md` 初始化 shadcn + tokens.css

**方向对齐**：✅ 现代化 UI 有明确定义，不改变 v1 parity 范围

---

### 2026-06-29 — 仓库规范与协作文档初版

**变更摘要**

- 新增 `.gitignore`：排除 `/coding/` 上游源码目录
- 新增 `AGENTS.md`：AI 协作规则（边界、迁移流程、测试）
- 新增 `CONTEXT.md`（本文件）：方向锚点 + **实现更新记录**
- 新增设计规格 `docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md`
- Brainstorming 结论写入设计规格：Tauri 2、全量 React、strict parity、uv、1 人全职

**影响范围**

- 仅文档与 Git 策略，**无**运行时代码

**验证**

- [x] `coding/` 已在 `.gitignore`
- [ ] 根目录 `git init`（待用户执行）

**下一步**

- Phase 0：根目录 `pyproject.toml` + `services/api` 最小可启动骨架
- 导出 `tests/fixtures/openapi_baseline.json`（对照 `coding/Infinite-Canvas`）

**方向对齐**：✅ 符合 v1 迁移路线，未引入 Agent 调度或 scope 外功能

---

<!-- 新记录插入在此线之上 -->

---

## 4. 更新日志书写模板（Agent 复制使用）

```markdown
### YYYY-MM-DD — 标题

**变更摘要**
- 

**影响范围**
- 模块 / 路径：

**验证**
- [ ] 

**下一步**
- 

**方向对齐**：✅ / ⚠️ 说明
```

---

## 5. 相关文档

| 文档 | 用途 |
|------|------|
| `CONTEXT.md` | 方向 + **每次更新的记录** |
| `AGENTS.md` | AI 硬性规则与迁移流程 |
| `DESIGN.md` | **视觉规范**（Token、布局、组件、画布） |
| `docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md` | 完整架构设计规格 |
| `coding/Infinite-Canvas/` | 上游源码（本地，gitignore） |
