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

**当前阶段**：`M9 — 无限画布 Batch 3 完成`（运行编排 + 连线输入解析；Tauri 待做）

**当前里程碑进度**：

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0 基线 / 文档 | ✅ 完成 | `.gitignore`、`AGENTS.md`、`CONTEXT.md`、`DESIGN.md`、设计规格 |
| M1 uv 后端壳 | ✅ 完成 | `pyproject.toml`、`infinite_canvas` 包、health/app-info、static 挂载 |
| M2–M3 后端 100% parity | ✅ 完成 | 已迁移 **126** legacy OpenAPI paths |
| M4 前端 Shell | ✅ 完成 | pnpm monorepo、Design System、14 路由 |
| M5 设置页 | ✅ 完成 | API / ComfyUI 设置 |
| M6 列表/素材/对话 | ✅ 完成 | 画布列表、素材库、GPT 对话 |
| M7 工具页 | ✅ 完成 | zimage / enhance / klein / online / angle |
| M8 智能画布 | ✅ 完成 | `/smart/:id` 卡片布局、拖拽、CRUD、自动保存 |
| M9 无限画布 + Tauri | 🟡 进行中 | Batch 3：图解析 + 运行编排 + 日志面板；Tauri 待做 |

---

## 2. 实现范围速查（迁移清单）

<details>
<summary>点击展开：后端 / 前端 / 集成（与 design spec 一致）</summary>

### 后端（147 HTTP + `/ws/stats`）

- 源：`coding/Infinite-Canvas/main.py`（~15k 行）→ 目标：`services/api/src/infinite_canvas/`

### 前端（14 页 → React）

| 原 HTML | 计划路由 | 迁移状态 |
|---------|----------|----------|
| index.html | `/` | 🟡 路由占位 |
| canvas-list.html | `/canvases` | 🟡 核心 CRUD |
| canvas.html | `/canvas/:id` | 🟡 @xyflow 编辑器 + 14 节点 + Batch 3 运行编排 |
| smart-canvas.html | `/smart/:id` | 🟡 卡片 CRUD + 自动保存 |
| asset-manager.html | `/assets` | 🟡 资产库 Tab 核心 |
| api-settings.html | `/settings/api` | 🟡 核心 CRUD |
| comfyui-settings.html | `/settings/comfyui` | 🟡 实例+工作流配置 |
| gpt-chat.html | `/chat` | 🟡 流式对话核心 |
| zimage / enhance / klein / online / angle | `/tools/*` | 🟡 核心生成 |

> **M4 脚手架**（2026-06-29）：pnpm workspace、`apps/web`（Vite + shadcn + tokens + 产品型/工具型 Shell）、`packages/api-types` / `canvas-schema`、Playwright E2E happy path。业务逻辑均为 ⚪。

### 外部集成（v1 保持行为）

ComfyUI · API/APIMart · ModelScope · RunningHub · 火山 · 即梦 CLI · PS/Chrome 插件（localhost）

</details>

---

## 3. 更新日志（按时间倒序）

> Agent：**每次**完成有意义的代码/配置变更后，在**本表最上方**插入一条。  
> 格式：`### YYYY-MM-DD — 简短标题` + 变更摘要 + 影响范围 + 下一步。

---

### 2026-06-29 — M9 前端：无限画布 Batch 3 运行编排

**变更摘要**

- **`lib/graph.ts`**：`generatorSources` / `orderedSources` / `resolveRunPayload` / `findDownstreamOutput` / `CANVAS_GENERATOR_TYPES`（对齐上游 `canvas.js`）
- **`EditorActionsContext`** 扩展：`getRunContext` / `appendLog` / `writeOutputImages` + `nodes` / `edges`
- 重构 **Generator / MsGen / Comfy / Video / LLM / RH** 节点：上游 prompt + reference_images；`generatedOutputs` + 下游 output 写入
- **`LoopNode`** 简化串行运行 + 作为 generator 输入源
- **`LogsPanel`** 右侧抽屉；`CanvasFlow` 多选/删除/`onConnect` 同步 inputs
- E2E：generator prompt 预览 + 日志 toggle

**影响路径**

- `apps/web/src/features/canvas/lib/graph.ts`
- `apps/web/src/features/canvas/lib/runHelpers.ts`
- `apps/web/src/features/canvas/components/**`
- `tests/e2e/m9-canvas-editor.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m9-canvas-editor.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **11 passed**

**下一步**

- M9 Batch 4：级联 `runNodeCascade`、LTX 时间轴、撤销栈、资产库侧栏
- Tauri 2 桌面打包

**方向对齐**

- 单节点运行已消费连线输入并写 output；全链级联与高级模式 UI 待 Batch 4

---

### 2026-06-29 — M9 前端：无限画布 Batch 2 节点类型

**变更摘要**

- **`packages/canvas-schema/src/nodes.ts`**：新增 `BATCH2_NODE_TYPES`（msgen/comfy/rh/video/llm/loop/text/ltxDirector/promptGroup）及 defaultData（对齐上游 `canvas.js`）
- React 节点组件 9 类 + **`FallbackNode`**（未知 type 保留 JSON preview）
- **`serialize.ts`**：未注册 type → `fallback` 渲染；保存时还原 `nodeType`
- **`api.ts`**：`canvas-video`、`canvas-llm`、`ms/generate`、`canvas-comfy-tasks`、`runninghub/submit|query`
- **`CreateMenu`**：分组展示 Batch 1 + Batch 2
- E2E 扩展：CreateMenu Batch2 选项 + Fallback 断言
- 计划文档 Batch 2 章节 + Batch 3 缺口

**影响路径**

- `packages/canvas-schema/src/**`
- `apps/web/src/features/canvas/**`
- `tests/e2e/m9-canvas-editor.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m9-canvas-editor.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **10 passed**

**下一步**

- M9 Batch 3：级联运行、连线输入解析、loop/LTX 完整逻辑
- Tauri 2 桌面打包

**方向对齐**

- 无限画布全部 14 类节点已有 UI 与 data 兼容；运行队列与编排待 Batch 3

---

### 2026-06-29 — M9 前端：无限画布 `/canvas/:id`（Batch 1）

**变更摘要**

- 安装 **`@xyflow/react`**；`CanvasEditorPage` 替换为可用节点图编辑器
- `GET/PUT /api/canvases/:id` 读写画布 JSON（`nodes` / `connections` / `viewport` 与上游兼容）
- 450ms 防抖自动保存；点阵网格背景（`--canvas-bg` / `--canvas-grid`）
- **`packages/canvas-schema/src/nodes.ts`**：节点注册表 + Batch 1 五类节点默认 data
- React 节点组件：`image` · `prompt` · `output` · `group` · `generator`（运行调 `/api/canvas-image-tasks`）
- xyflow edges ↔ `connections[{id,from,to}]`；左侧 FAB 创建菜单
- `CanvasShell` 顶栏：标题编辑 + 保存状态（context 联动）
- E2E：`tests/e2e/m9-canvas-editor.spec.ts`
- 计划：`docs/superpowers/plans/2026-06-29-phase2-frontend-m9-canvas-editor.md`

**影响路径**

- `apps/web/package.json`、`apps/web/src/features/canvas/**`
- `apps/web/src/components/shell/CanvasShell.tsx`
- `packages/canvas-schema/src/**`
- `tests/e2e/m9-canvas-editor.spec.ts`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **10 passed**

**下一步**

- M9 Batch 2：msgen / comfy / rh / video / llm / loop 等节点 parity
- Tauri 2 桌面打包

**方向对齐**

- 14 页前端 UI 已全部有核心实现；无限画布剩余节点类型与运行队列待补

---

### 2026-06-29 — M8 前端：智能画布 `/smart/:id`

**变更摘要**

- **`/smart/:id`**：全屏 `SmartCanvasShell`；加载/自动保存 `GET/PUT /api/canvases/:id`
- 四类卡片：`smart-image` / `smart-prompt` / `smart-group` / `smart-loop`；创建菜单、拖拽移动、删除
- 视口平移缩放；媒体上传 `POST /api/ai/upload`；分组导出 API 封装
- E2E：`tests/e2e/m8-smart-canvas.spec.ts`

**影响路径**

- `apps/web/src/features/smart-canvas/**`
- `apps/web/src/components/shell/SmartCanvasShell.tsx`
- `apps/web/src/app/router.tsx`
- `tests/e2e/m8-smart-canvas.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m8-smart-canvas.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **9 passed**

**下一步**

- M9 无限画布 `/canvas/:id`（@xyflow/react + 节点注册表）
- Tauri 2 桌面打包

**方向对齐**

- 14 页中 13 页已有核心 UI；无限画布为 v1 最后大块

---

### 2026-06-29 — M7 前端：Studio 五个工具页

**变更摘要**

- **`/tools/zimage`**：本地 ComfyUI / ModelScope 云端文生图 + 历史
- **`/tools/enhance`**：图片上传、强度调节、本地 Enhance / MS Klein LoRA
- **`/tools/klein`**：多图上传、本地 Flux2-Klein / 云端 MS 编辑
- **`/tools/online`**：平台/模型/尺寸、参考图、`/api/online-image`
- **`/tools/angle`**：方位角/仰角滑块、云端 Qwen 视角生成 + poll
- 共享 `ToolLayout`、`HistoryMasonry`、`features/tools/api.ts`；Vite 代理 `/generate`

**影响路径**

- `apps/web/src/features/tools/**`
- `apps/web/vite.config.ts`
- `tests/e2e/m7-tools.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m7-tools.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **8 passed**

**下一步**

- M9 无限画布 `/canvas/:id`（@xyflow/react + 节点注册表）

**方向对齐**

- 14 页中 13 页已有核心 UI；无限画布为 v1 最后大块

---

### 2026-06-29 — M6 前端：画布列表 / 素材库 / GPT 对话

**变更摘要**

- **`/canvases`**：项目侧栏、画布卡片网格、新建画布/项目、删除、回收站恢复与永久删除；链接至 `/canvas/:id` 或 `/smart/:id`
- **`/chat`**：会话列表、SSE 流式 `/api/chat/stream`、平台/模型选择（`/api/config`）
- **`/assets`**：资产库/分类浏览、multipart 上传 → batch add、多选删除
- E2E：`tests/e2e/m6-pages.spec.ts`（3 页 mock happy path）

**影响路径**

- `apps/web/src/features/canvas/`、`chat/`、`assets/`
- `apps/web/src/lib/api/upload.ts`
- `tests/e2e/m6-pages.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m6-core-pages.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e` → **6 passed**

**下一步**

- M6 补全：看板拖拽、素材库多 Tab、对话图片模式
- M7：Studio 工具页（zimage/enhance/klein/online/angle）

**方向对齐**

- 按迁移顺序推进；三页核心数据流已通；legacy 高级 UI 分后续小批补全

---

### 2026-06-29 — M5 前端：API 设置与 ComfyUI 工作流设置

**变更摘要**

- **`/settings/api`**：平台列表、新增/删除、基本信息与协议、Key（标准/RH 双 Key/火山 AK-SK）、模型列表编辑、测试连接、拉取上游模型；TanStack Query + `SaveProviderPayload` 对接 `PUT /api/providers`
- **`/settings/comfyui`**：ComfyUI 实例 CRUD、工作流列表、JSON 上传、暴露字段配置保存/删除；对接 `/api/comfyui/instances`、`/api/workflows/*`
- 共享 `SettingsPageLayout`、shadcn Label/Textarea；`AppProviders` 接入 QueryClient
- Playwright：`tests/e2e/settings-pages.spec.ts`（mock API happy path）

**影响路径**

- `apps/web/src/features/settings/**`
- `apps/web/src/app/AppProviders.tsx`
- `apps/web/src/components/ui/label.tsx`、`textarea.tsx`
- `tests/e2e/settings-pages.spec.ts`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m5-settings.md`

**验证项**

- [x] `pnpm --filter web build`
- [x] `pnpm test:e2e`（3 passed：app-shell + settings-pages）
- [ ] 联调：`uv run infinite-canvas --port 3000` + `pnpm dev` → 保存 providers / workflow config

**下一步**

- M5 补全：推荐 API、RH 工作流编辑器、ComfyUI 节点图预览与运行测试
- M6：素材库 + 画布列表 + GPT 对话

**方向对齐**

- strict parity 按页推进；设置页核心数据流已通；legacy 高级 UI（图编辑器）分后续小批补全

---

### 2026-06-29 — M4 前端 monorepo 与 Design System 脚手架

**变更摘要**

- 根目录 **pnpm monorepo**：`package.json`（`dev`/`build`/`lint`/`test:e2e` 脚本）、`pnpm-workspace.yaml`（`apps/*`、`packages/*`）
- **`apps/web`**：Vite 6 + React 18 + TypeScript + Tailwind 3 + shadcn/ui（new-york）；已装 button/card/input/tabs/dialog/command/sheet/sonner
- **`DESIGN.md` Token 落地**：`src/styles/tokens.css`（light/dark + 画布专用变量）、`globals.css`；`lib/theme.ts` 主题持久化（兼容 legacy `canvas_theme`）
- **B+ 布局壳**：`components/shell/Sidebar.tsx`（可折叠侧栏）；`lib/navigation.ts` 映射 14 页路由与面包屑
- **API 层**：`lib/api/client.ts` 复用 `@infinite-canvas/api-types`；Vite proxy 对接后端 `/api`、`/ws`、`/static`、`/assets`、`/output`
- **`packages/api-types`**：`createApiClient()` 泛型 HTTP 客户端 + OpenAPI 生成占位脚本（读 `openapi_baseline.json`）
- **`packages/canvas-schema`**：画布节点注册表类型 stub（M5+ 分批填充）
- **待补**：`main.tsx` / `App.tsx`、React Router 布局、TanStack Query / Zustand、业务 feature 页

**影响路径**

- `package.json`、`pnpm-workspace.yaml`（根目录，未跟踪）
- `apps/web/`（Vite、shadcn、styles、shell、lib）
- `packages/api-types/`、`packages/canvas-schema/`

**验证项**

- [ ] `pnpm install && pnpm --filter web dev`（需补齐 App 入口后）
- [ ] tokens.css 与 `DESIGN.md` §2 变量对照
- [ ] Vite proxy 联调 `uv run infinite-canvas --port 3000`

**下一步**

- 补齐 `main.tsx` + Router 布局壳（Sidebar + Outlet）
- 按 AGENTS.md 顺序首迁设置页（`/settings/api` → `/settings/comfyui`）

**方向对齐**

- M4 启动符合迁移顺序（Design System → 设置页 → … → canvas 最后）；无 API 契约变更；strict parity 页面迁移尚未开始

---

### 2026-06-29 — M4 Phase：Design System + App Shell + 路由脚手架

**变更摘要**

- 新建 pnpm monorepo 根（`package.json`、`pnpm-workspace.yaml`）
- `apps/web`：React 18 + Vite + Tailwind + shadcn/ui；`tokens.css` 落地 DESIGN.md §2；产品型 B+ Shell（侧栏 64/240px、顶栏面包屑、主题切换 `studio_theme`）与工具型 Canvas Shell stub
- 14 页路由占位 + Cmd+K Command 面板；`packages/api-types`（client 封装）、`packages/canvas-schema`（节点注册表 stub）
- Vite 代理 `/api`、`/ws`、`/static`、`/assets`、`/output` → `127.0.0.1:3000`
- Playwright E2E：`tests/e2e/app-shell.spec.ts`（侧栏、主题、导航 `/canvases`）

**影响路径**

- `package.json`、`pnpm-workspace.yaml`
- `apps/web/**`
- `packages/api-types/**`、`packages/canvas-schema/**`
- `tests/e2e/**`
- `docs/superpowers/plans/2026-06-29-phase2-frontend-m4-shell.md`

**验证项**

- `pnpm install && pnpm --filter web build`
- `pnpm --filter e2e test`
- 后端 pytest 未改动，仍应全绿

**下一步**

- M4 续：设置页（API / ComfyUI）业务迁移
- 素材库、聊天、tools 页逐批 parity

**方向对齐**

- v1 strict parity；本批仅 Shell + 路由占位，无 API 契约变更

---

### 2026-06-29 — Phase 1 Batch 9：Avatar / 多平台生图 / Canvas Video 完整迁移

**变更摘要**

- 消除全部后端 501 stub：资产库 Avatar 注册（APIMart + 火山）、五平台 `generate_ai_image`、画布视频全 provider 分支（即梦/RunningHub/APIMart/火山/Agnes/玉玉 + 轮询）
- 新增 8 个 service 模块：`avatar`、`apimart_media`、`volcengine_assets`、`provider_helpers`、`provider_image`、`jimeng_generate`、`runninghub_provider`、`video_tasks`；`canvas_video.py` 完整替换为 legacy parity
- 测试：pytest **106 passed**；OpenAPI baseline **126 paths** 不变

**影响路径**

- `services/api/src/infinite_canvas/services/{avatar,apimart_media,volcengine_assets,provider_helpers,provider_image,jimeng_generate,runninghub_provider,video_tasks,canvas_video,online_image}.py`
- `services/api/src/infinite_canvas/routes/asset_libraries.py`
- `tests/api/test_{asset_library_crud,online_image,canvas_ai}.py`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch9.md`

**验证项**

- `uv run pytest tests/api -v` 全绿
- `rg '501|尚未迁移' services/` 无匹配

**下一步**

- 启动 M4 前端 React 迁移（Design System → 设置页）

**方向对齐**

- v1 strict parity 后端域已闭环；无 API 契约变更

---

### 2026-06-29 — Phase 1 Batch 8：聊天、画布 AI、角度生成与 GitHub 更新

**变更摘要**

- 新增 `services/chat.py`、`routes/chat.py`（**3** 端点：`/api/chat`、`/api/chat/stream`、`/api/chat/agent` legacy parity）
- 新增 `services/canvas_llm.py`、`canvas_video.py`、`modelscope_generate.py`、`routes/canvas_ai.py`（**4** 端点含 `/generate` 云端 Z-Image）
- 新增 `routes/angle.py`（**2** 端点）、`services/smart_canvas.py`（group-export）
- 新增 `services/cloud_upload.py`（temp-sh / cloud-video）、`services/app_update.py`（**6** 更新端点）
- 测试：`test_chat.py`、`test_canvas_ai.py`、`test_angle.py`、`test_update.py`；OpenAPI baseline **126 paths**

**影响路径**

- `services/api/src/infinite_canvas/services/`、`routes/`、`schemas/`
- `tests/api/`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch8.md`

**验证项**

- `uv run pytest tests/api -v` → **103 passed**
- legacy OpenAPI 路径全覆盖（`missing: []`）

**下一步**

- 启动 M4 前端 Design System + 设置页迁移
- 画布节点分批 parity（canvas 页最后）

**方向对齐**

- v1 strict parity；`/api/chat/agent` 仅 legacy 路由，无 Agent 调度画布

---

### 2026-06-29 — Phase 1 Batch 7：AI 上传、画布资产与在线生图

**变更摘要**

- 新增 `services/ai_upload.py`、`routes/ai_upload.py`（**3** 端点：`/api/ai/upload`、`upload-base64`、`import-local-image`）
- 新增 `services/canvas_assets.py`、`services/canvas_workflows.py`、`routes/canvas_assets.py`（**8** 端点：canvas-assets、prompt-templates、check、download、workflow export/import/library）
- 新增 `services/online_image.py`、`routes/online_image.py`（**4** 端点：online-image、image-task-query、canvas-image-tasks）；OpenAI 兼容同步生图 + APIMart 轮询；复用 `comfyui_generate.CANVAS_TASKS`
- 扩展 `asset_library_store`（`make_workflow_library_item_from_bytes`、`asset_library_workflow_category`）
- 新增 `tests/api/test_ai_upload.py`、`test_canvas_assets.py`、`test_online_image.py`；OpenAPI **108 paths**

**影响路径**

- `services/api/src/infinite_canvas/services/ai_upload.py`、`canvas_assets.py`、`canvas_workflows.py`、`online_image.py`
- `services/api/src/infinite_canvas/routes/ai_upload.py`、`canvas_assets.py`、`online_image.py`、`routes/__init__.py`
- `services/api/src/infinite_canvas/schemas/ai_upload.py`、`canvas_assets.py`、`online_image.py`
- `services/api/src/infinite_canvas/services/asset_library_store.py`
- `tests/api/test_ai_upload.py`、`test_canvas_assets.py`、`test_online_image.py`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch7.md`

**验证项**

- [x] `uv run pytest tests/api -v` → **90 passed**
- [x] `uv run python scripts/export_openapi_baseline.py` → **108 paths**

**下一步**

- Batch 8：chat 域、canvas-video-tasks、火山 volcengine 生图完整移植

**方向对齐**

- strict parity；AI 参考图落 `assets/input`；画布资产索引扫描全库画布 JSON；非 OpenAI 平台生图 stub 501 待后续批次

---

### 2026-06-29 — Phase 1 Batch 6：RunningHub + 即梦 jimeng

**变更摘要**

- 新增 `services/runninghub.py`、`routes/runninghub.py`、`schemas/runninghub.py`（**12** 端点：app-info、submit、workflow CRUD、query、upload-asset）
- 新增 `services/jimeng.py`、`routes/jimeng.py`、`schemas/jimeng.py`（**8** 端点：status、credit、login/logout、help、query-media）；保留 WSL/原生平台分支与 `JimengPendingError` → 202 handler
- 扩展 `core/paths.py`（`runninghub_workflow_store_file()`）；`provider_probe` 改从 `jimeng` 模块导入 status
- 新增 `tests/api/test_runninghub.py`、`test_jimeng.py`；OpenAPI **93 paths**

**影响路径**

- `services/api/src/infinite_canvas/services/runninghub.py`、`jimeng.py`
- `services/api/src/infinite_canvas/routes/runninghub.py`、`jimeng.py`、`routes/__init__.py`
- `services/api/src/infinite_canvas/schemas/runninghub.py`、`jimeng.py`
- `services/api/src/infinite_canvas/app.py`、`core/paths.py`
- `tests/api/test_runninghub.py`、`test_jimeng.py`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch6.md`

**验证项**

- [x] `uv run pytest tests/api -v` → **76 passed**
- [x] `uv run python scripts/export_openapi_baseline.py` → **93 paths**

**下一步**

- Batch 7：chat 域、canvas-image-tasks、或火山 volcengine 剩余端点

**方向对齐**

- strict parity；RunningHub 工作流 store 与 provider `rh_workflows` 同步逻辑与 legacy 一致；即梦 CLI subprocess 行为未改 API 契约

---

### 2026-06-29 — Phase 1 Batch 5：ComfyUI 实例/工作流 + generate + canvas-comfy-tasks

**变更摘要**

- 新增 `services/comfyui_workflows.py`、`services/comfyui_generate.py`、`routes/comfyui.py`、`schemas/comfyui.py`
- **~14** 个端点：`/api/comfyui/instances`、`/api/workflows/*`、`/api/generate`、`/api/canvas-comfy-tasks/*`、`/api/comfyui/upload-base64`、`/api/image-params`
- 扩展 `core/paths.py`（`workflows_dir`）、`core/comfyui.py`（`save_instances`、负载均衡）、`core/queue.py`（`NEXT_TASK_ID`）、`services/history.py`（`save_to_history`）
- 新增 `tests/api/test_comfyui.py`、`test_generate.py`；OpenAPI **77 paths**

**影响路径**

- `services/api/src/infinite_canvas/core/`、`services/`、`routes/comfyui.py`、`schemas/comfyui.py`
- `tests/api/test_comfyui.py`、`test_generate.py`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch5.md`

**验证项**

- [x] `uv run pytest tests/api -v` → **70 passed**

**下一步**

- Batch 6：chat 域、runninghub、或 canvas-image-tasks

**方向对齐**

- 工作流目录 `{app_data}/workflows/custom/`；内置 JSON 回退 `coding/Infinite-Canvas/workflows/`；generate 保持 legacy JSON 形状与 QUEUE/history/WS 广播

---

### 2026-06-29 — Phase 1 Batch 4b：资产库/提示词库 CRUD + shared_folders

**变更摘要**

- 扩展 `prompt_library_store.py`（`find_prompt_library`）；新增 `routes/prompt_libraries.py`：**10** 个 `/api/prompt-libraries/*` CRUD 端点
- 扩展 `asset_library_store.py`（`find_*`、`make_asset_library_item`、`remove_asset_library_file`、`unique_asset_category_dir`、`asset_library_media_kind`）；扩展 `routes/asset_libraries.py`：**~15** 个资产库 CRUD（avatar 注册/状态 → **501 尚未迁移**）
- 新增 `services/shared_folders_store.py`、`routes/shared_folders.py`：**6** 个 `/api/shared-folders/*` 端点；登记根目录为 `app_data_dir()`
- 新增 `schemas/asset_libraries.py`；`core/paths.py` 增加 `shared_folders_file()`
- 新增 `tests/api/test_prompt_library_crud.py`、`test_asset_library_crud.py`、`test_shared_folders.py`；OpenAPI **67 paths**

**影响路径**

- `services/api/src/infinite_canvas/services/`、`routes/`、`schemas/asset_libraries.py`、`core/paths.py`
- `tests/api/test_*_crud.py`、`test_shared_folders.py`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch4b.md`

**验证项**

- [x] `uv run pytest tests/api -v` → **62 passed**

**下一步**

- Batch 5：comfyui / chat 域；或 `workflows/upload`、avatar 注册迁移

**方向对齐**

- shared_folders 路径校验基于桌面数据根 `app_data_dir()`；资产库文件 URL `/assets/library/*` 由既有静态挂载服务

---

### 2026-06-29 — Phase 1 Batch 4：local_assets + 资产库/提示词库基础

**变更摘要**

- 新增 `services/local_assets.py`、`routes/local_assets.py`、`schemas/local_assets.py`：**11** 个 `/api/local-assets/*` 端点（upload/import/list/folders/items/delete/move/caption/classify）
- 新增 `services/asset_ai.py`（caption/classify 上游 vision 调用）、`core/security.py`（同源校验）、`core/asset_utils.py`（分类 JSON 规范化）
- 扩展 `core/paths.py`：`local_upload_dir()`、`asset_library_*`、`prompt_libraries_file()`；`app.py` 优先挂载 `{app_data}/assets`
- 新增 `services/asset_library_store.py`、`services/prompt_library_store.py`、`routes/asset_libraries.py`：`GET /api/asset-library`、`GET /api/prompt-libraries`
- 新增 `tests/api/test_local_assets.py`（5 条）；OpenAPI **43 paths**

**影响路径**

- `services/api/src/infinite_canvas/core/`、`services/`、`routes/`、`schemas/local_assets.py`
- `tests/api/test_local_assets.py`、`tests/fixtures/openapi_baseline.json`
- `docs/superpowers/plans/2026-06-29-phase1-backend-batch4.md`

**验证项**

- [x] `uv run pytest tests/api -v` → **53 passed**

**下一步**

- Batch 4 剩余：asset_library / prompt_libraries CRUD、shared_folders；或 Batch 5 comfyui/chat 域

**方向对齐**

- 本地素材文件存 `{app_data}/assets/uploads`；资产库/提示词库 JSON 存 `{app_data}/data/`；HTTP 契约与 legacy 一致

---

### 2026-06-29 — SQLite 本地数据库存储（画布 / 配置 / 对话）

**变更摘要**

- 新增 `core/database.py`：SQLite（WAL）单文件 `{app_data}/infinite-canvas.db`，表 `canvases` / `projects` / `conversations` / `app_settings`
- 新增 `services/data_migration.py`：启动时自动从 JSON 文件导入；`POST /api/data/migrate-from-files` 手动/强制迁移
- 新增 `routes/data_store.py`：`GET /api/data/store`（路径、统计、配置键列表）
- 接入 `canvas_store` / `projects` / `conversations` / `provider_store`：默认 **sqlite** 模式；`INFINITE_CANVAS_STORAGE=files` 回退纯 JSON
- API 密钥仍存 `config/.env`；API 平台列表存 DB `app_settings.api_providers`
- 新增 `tests/api/test_database_storage.py`（6 条）；OpenAPI **32 paths**

**影响路径**

- `core/database.py`、`services/data_migration.py`、`routes/data_store.py`
- `services/canvas_store.py`、`projects.py`、`conversations.py`、`provider_store.py`
- `app.py`、`routes/system.py`（app-info 含 storage/database_path）

**验证项**

- [x] `uv run pytest tests/api -v` → **48 passed**

**下一步**

- Batch 4 assets 域迁移；Tauri sidecar 使用 `--data-dir` 指向同一 DB 文件

**方向对齐**

- 桌面端单文件 DB 便于备份/迁移；HTTP API 契约不变；兼容 legacy JSON 一次性导入

---

### 2026-06-29 — Phase 1 Task 7：Providers + Config + Models 迁移

**变更摘要**

- 新增 `core/env_file.py`（`load_env_file` / `update_env_values`，路径 `{app_data}/config/.env`）
- 新增 `core/provider_constants.py`、`core/runtime_config.py`（`reload_env_globals` 模块级模型列表同步）
- 新增 `services/provider_store.py`（load/save/normalize/public/merge 默认平台）
- 新增 `services/provider_probe.py`（test-connection、probe-async、fetch-models、RunningHub 注册表兜底）
- 新增 `schemas/provider.py`、`routes/providers.py`（9 端点：config/models/providers/token/test/probe/fetch）
- 扩展 `core/paths.py`：`api_env_file()`、`api_providers_file()`、`conversations_dir()`、`global_config_file()`
- 新增 `tests/api/test_providers.py`（6 条）；`openapi_baseline.json` 更新至 **30 paths**

**影响路径**

- `services/api/src/infinite_canvas/core/`、`services/`、`routes/providers.py`、`tests/api/test_providers.py`
- `tests/fixtures/openapi_baseline.json`

**验证项**

- `uv run pytest tests/api -v` → **42 passed**
- `GET /api/config`、`PUT /api/providers`、`GET /api/config/token`、jimeng test-connection stub

**下一步**

- Phase 1 Batch 4：assets / comfyui / chat 等域

**方向对齐**

- env 与 providers JSON 路径对齐 design spec §5.3；API 契约与 legacy 一致；即梦 full module 留后续批次

---

### 2026-06-29 — Phase 1 Task 6：Conversations CRUD 迁移

**变更摘要**

- 新增 `services/conversations.py`：`safe_user_id`、`X-User-Id` header、按用户目录 JSON 存储
- 新增 `schemas/conversation.py`、`routes/conversations.py`（4 端点：list/create/get/delete）
- 数据目录：`{app_data_dir()}/data/conversations/{user_id}/*.json`
- 新增 `tests/api/test_conversations.py`（3 条：空列表、CRUD、用户隔离）

**影响路径**

- `services/api/src/infinite_canvas/services/conversations.py`
- `routes/conversations.py`、`schemas/conversation.py`、`core/paths.py`
- `tests/api/test_conversations.py`

**验证项**

- `uv run pytest tests/api/test_conversations.py -v` → 3 passed

**下一步**

- Task 7 providers/config（同 Batch 3）

**方向对齐**

- 对话存储与 legacy `CONVERSATION_DIR` 行为一致；v1 parity，无新特性

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
