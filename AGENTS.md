# AGENTS.md — AI 协作规则

本文件约束在本仓库工作的 AI Agent（Cursor、Codex 等）。阅读顺序：**CONTEXT.md → DESIGN.md（UI 任务）→ 本文件 → 架构设计规格**。

---

## 1. 项目目标

在 **仓库根目录 `ai-canvas/`** 完成 Infinite-Canvas 的：

1. **全量功能迁移**（strict parity，v1 不增新特性）
2. **uv 后端模块化**
3. **React 现代化 UI 全量重写**
4. **Tauri 2 桌面打包**（Windows + macOS）

架构设计规格：`docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md`  
视觉规范：**`DESIGN.md`**（所有 `apps/web` UI 必须遵循）

---

## 2. 硬性规则

### 2.0 CONTEXT.md 维护（必做）

| 时机 | 动作 |
|------|------|
| **每次会话开始** | 阅读 `CONTEXT.md` §1 方向锚点、§3 最新一条更新日志 |
| **每次提交级代码变更后** | 在 `CONTEXT.md` §3 **最上方**追加一条记录（用 §4 模板） |
| **里程碑完成 / scope 变更** | 同步更新 §1 当前阶段、里程碑进度表 |

记录须包含：**变更摘要、影响路径、验证项、下一步、方向对齐**。避免 Agent 接力时偏离 v1 parity 目标。

**项目 Hook 自动提醒**（`.cursor/hooks.json`）：主 Agent 结束（`stop`）或 Task 子 Agent 结束（`subagentStop`）时，若 `git status` 显示 `services/`、`apps/`、`tests/`、`scripts/`、`packages/`、`pyproject.toml` 或 `package.json` 有改动而 `CONTEXT.md` 未同步更新，Hook 会通过 `followup_message` 要求补写 §3 日志。Agent **必须响应**该 follow-up，按 §4 模板更新 `CONTEXT.md`（必要时同步 §1），再继续结束会话。

### 2.1 源码边界

| 规则 | 说明 |
|------|------|
| **不要修改 `coding/` 并提交** | `coding/` 为 gitignore 的上游对照树，仅本地阅读、diff、parity 测试 |
| **新代码写在根目录规范路径** | `apps/`、`services/`、`packages/`、`tests/` |
| **API 契约优先** | 迁移阶段不得改变 URL、请求/响应 JSON、WebSocket 消息格式，除非设计规格明确版本升级 |
| **v1 不做 Agent 调度画布** | 不新增 Plan/DAG/Run API；仅迁移现有 `/api/chat/agent` |
| **最小 diff** | 不重构无关模块；不顺手改样式/依赖，除非任务要求 |

### 2.2 技术栈与视觉（不得擅自替换）

- Python：**uv** + FastAPI + uvicorn  
- 前端：React + TypeScript + Vite + Tailwind + shadcn/ui  
- 画布：`@xyflow/react`  
- 桌面：**Tauri 2** + Python sidecar  
- **视觉**：严格遵循 **`DESIGN.md`**（Token、双模式布局、节点样式）；禁止第二套色板或 UI 库

### 2.3 许可证

- 二开须注明 Infinite-Canvas 原作者  
- 不要移除原项目版权声明  
- 商用封装需用户自行取得授权  

---

## 3. 目录职责

```
apps/web/           → React UI，唯一用户界面源码
apps/desktop/       → Tauri 壳：sidecar 生命周期、托盘、对话框
services/api/       → FastAPI；业务在 services/，HTTP 在 routes/
packages/           → 共享类型（api-types、canvas-schema）
tests/api/          → pytest，对照 OpenAPI baseline
tests/e2e/          → Playwright，14 页 parity
coding/             → 【只读】上游 Infinite-Canvas，gitignore
reference/          → 可选小体积对照快照
docs/               → 设计与 ADR
```

**禁止**在 `apps/web` 之外新增用户可见 UI 逻辑（除 Tauri 原生对话框）。

---

## 4. 迁移工作流

### 4.1 后端拆模块

1. 从 `coding/Infinite-Canvas/main.py` 定位 handler  
2. 提取到 `services/<domain>.py`  
3. 在 `routes/<domain>.py` 注册路由  
4. 添加 `tests/api/test_<domain>.py`  
5. 与 baseline OpenAPI / 旧行为对比  

拆分顺序见设计规格 §5.2（upload → canvases → assets → providers → comfyui → …）。

### 4.2 前端迁页面

1. 对照 `coding/Infinite-Canvas/static/<page>.html` 与同页 JS  
2. 在 `apps/web/src/features/<name>/` 实现  
3. 使用 `packages/api-types` 调用 API  
4. 补充 Playwright 用例  

顺序：Design System → 设置 → 素材/列表/chat → tools → smart-canvas → **canvas（最后）**。

### 4.3 Parity 定义

- 功能与旧版一致，UI 可现代化  
- 画布 JSON 须与旧 `data/canvases/*.json` **兼容读写**  
- 14 项手工清单 + E2E 全绿才标记里程碑完成  

---

## 5. 编码约定

### Python

- `requires-python >= 3.10`  
- 类型注解：公共 service 函数必须标注  
- 配置：`core/config.py` + 环境变量，不散落 `os.getenv`  
- 路径：只用 `core/paths.py`，禁止硬编码 `BASE_DIR/data`  
- 格式化：`ruff check` / `ruff format`  

### TypeScript / React

- 严格模式；禁止 `any`（除非注释理由）  
- 组件：`components/ui`（shadcn） vs `features/*`（业务）  
- API：经 `lib/api` 封装，不直接在组件里拼 URL  
- 状态：Zustand（画布/UI）+ TanStack Query（服务端）  

### Git 提交

- 中文 Conventional Commits（见用户规则）  
- **仅用户要求时**才 `git commit`  
- ** never commit `coding/`**  

---

## 6. 测试要求

| 变更类型 | 最低要求 |
|----------|----------|
| 新增/迁移 API | pytest smoke + 必要时对比旧响应 fixture |
| 迁移前端页 | Playwright 至少 1 条 happy path |
| 画布节点 | 节点类型注册 + 加载旧画布 JSON 用例 |
| Tauri | 启停 sidecar、关窗释放端口 |

Baseline OpenAPI 路径（首次 M0 生成）：`tests/fixtures/openapi_baseline.json`

---

## 7. 运行与调试

```bash
# 对照上游（coding 目录，需用户本地存在）
cd coding/Infinite-Canvas && uv run main.py

# 新后端（实现后）
uv sync && uv run infinite-canvas --port 3000

# 前端
pnpm install && pnpm --filter web dev

# 桌面
pnpm desktop:dev
# 或
pnpm --filter desktop dev
```

Sidecar 默认数据目录：`~/.infinite-canvas/`。开发可用 `--data-dir ./.infinite-canvas-dev`。

---

## 8. 常见陷阱

1. **端口 3000 占用** — 启动前检测或 `--port` 自动递增  
2. **关 Tauri 未杀 Python** — sidecar 必须随窗口退出  
3. **修改 coding/** — 只读；改新仓库代码  
4. **canvas 大爆炸重写** — 按节点类型分批，每批 parity  
5. **macOS WebView 差异** — 画布相关改动需在 macOS 实测  
6. **即梦 / WSL** — 迁移 `jimeng` 模块时保留平台分支  

---

## 9. 任务分级（Agent 自行判断）

| 级别 | 示例 | 做法 |
|------|------|------|
| S | 修 typo、补类型 | 直接改 |
| M | 迁一个 API 域、一个设置页 | 单 PR 范围，加测试 |
| L | canvas 节点类、Tauri 打包 | 先写子计划，对齐设计规格 |
| XL | 整库重写 | **禁止**；必须按里程碑拆分 |

---

## 10. 输出语言

- 与用户沟通：**简体中文**  
- 代码注释：中文或英文均可，与所在文件保持一致  
- 提交说明：**简体中文** Conventional Commits  

---

## 11. 文档更新

以下变更时**应同步更新 CONTEXT.md §1/§3、`DESIGN.md`（视觉变更）或架构设计规格**：

- 任何有意义的代码/配置合并  
- 里程碑完成或 scope 变更  
- 新增外部依赖或替换 Tauri/React major 版本  
- API breaking change（v1 原则上不允许）  

---

## 12. 快速链接

- 方向与更新记录：`CONTEXT.md`  
- 视觉规范：`DESIGN.md`  
- 视觉规范：`DESIGN.md`  
- 架构设计规格：`docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md`  
- 上游只读：`coding/Infinite-Canvas/`  
