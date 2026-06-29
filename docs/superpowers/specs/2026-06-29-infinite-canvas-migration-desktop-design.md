# Infinite-Canvas 全量迁移 + 桌面端设计规格

**日期**: 2026-06-29  
**状态**: 已批准（仓库根目录实施）  
**源项目**: `coding/Infinite-Canvas`（本地只读，**gitignore**）  
**目标项目**: 仓库根目录 `ai-canvas/`（monorepo）  
**协作文档**: `CONTEXT.md`、`AGENTS.md`、**`DESIGN.md`（视觉规范）**

---

## 1. 背景与目标

### 1.1 背景

Infinite-Canvas 当前为本地 Web 应用：单文件 `main.py`（~15k 行、147 HTTP + 1 WebSocket）、14 个静态 HTML 页（~45k 行 JS）。启动方式为 `python main.py`，浏览器访问 `http://127.0.0.1:3000/`。

### 1.2 目标

| 目标 | 说明 |
|------|------|
| **全量功能迁移** | 旧版 14 页 + 全部画布节点/能力 100% 可用（strict parity） |
| **目录规范化** | uv monorepo，后端模块化，便于二开 |
| **现代化 UI** | React + shadcn/ui + Tailwind（构建版），双模式布局 |
| **桌面端打包** | Tauri 2，Windows + macOS 安装包 |
| **v1 不含新功能** | Agent 调度画布等放到 v1.1+ |

### 1.3 非目标（v1）

- Agent 自动规划/执行画布 DAG
- Linux 桌面包
- 云端同步 / 多用户登录
- 捆绑 ComfyUI 或 Python 模型

### 1.4 约束

| 约束 | 值 |
|------|-----|
| 人力 | 1 人全职 |
| Python 包管理 | **uv** |
| 桌面壳 | **Tauri 2** |
| 许可证 | 二开须开源并注明原作者；商用需原作者授权 |

---

## 2. 需求摘要（Brainstorming 结论）

| 决策项 | 选择 |
|--------|------|
| 桌面平台 | Windows + macOS |
| 前端策略 | 全量 React 重写（含 canvas / smart-canvas） |
| 发布标准 | strict parity 全绿后才发安装包 |
| v1 范围 | 仅迁移，保证所有现有功能正常 |
| 预估周期 | 9～11 个月（全职 1 人） |

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│  apps/desktop (Tauri 2)                                  │
│  ├─ WebView → apps/web (React SPA)                      │
│  ├─ Sidecar → services/api (Python uvicorn)              │
│  └─ 托盘 / 单实例 / 原生文件对话框 / 深链接              │
└─────────────────────────────────────────────────────────┘
         │ HTTP + WebSocket (127.0.0.1:{port})
         ▼
┌─────────────────────────────────────────────────────────┐
│  services/api (FastAPI, uv)                              │
│  routes/ → services/ → core/                            │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  用户数据 ~/.infinite-canvas/  (或 %APPDATA%)            │
│  data/ · assets/ · config/.env                          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  外部: ComfyUI · API · ModelScope · RunningHub · 即梦 CLI
```

### 3.1 技术栈

| 层 | 技术 |
|----|------|
| 桌面 | Tauri 2 + Rust（仅壳层，业务不写 Rust） |
| 前端 | React 18 + TypeScript + Vite |
| UI | Tailwind CSS + shadcn/ui + Framer Motion |
| 无限画布 | `@xyflow/react` + 自定义节点注册表 |
| 后端 | FastAPI + uvicorn，**uv** 管理依赖 |
| 类型 | OpenAPI → `packages/api-types` |
| 测试 | pytest（API）+ Playwright（E2E parity） |

### 3.2 现代化 UI 方向：**B+ 双模式**

- **产品型 Shell**（默认）：侧栏导航、留白、Linear/Notion 气质 — 用于首页、列表、设置、素材库
- **工具型布局**（画布内）：顶栏 + 浮动工具栏、高密度 — 用于无限画布编辑态
- 深浅色主题统一由 Design Tokens 驱动

---

## 4. 仓库结构

```
ai-canvas/                      # 仓库根目录
├── AGENTS.md                   # AI 协作规则
├── CONTEXT.md                  # 方向 + 实现更新记录
├── DESIGN.md                   # 视觉设计规范
├── AGENTS.md                   # AI 协作规则
├── .gitignore                  # 含 /coding/
├── pyproject.toml              # uv 根配置
├── uv.lock
├── package.json                # pnpm workspace 根
├── pnpm-workspace.yaml
│
├── coding/                     # 上游 Infinite-Canvas（gitignore，仅本地）
│
├── apps/
│   ├── desktop/                # Tauri 2
│   │   ├── src-tauri/
│   │   │   ├── tauri.conf.json
│   │   │   ├── sidecar/        # 打包后的 Python 可执行文件
│   │   │   └── src/main.rs     # 启停 sidecar、单实例
│   │   └── package.json
│   │
│   └── web/                    # React SPA
│       ├── src/
│       │   ├── app/            # 路由、布局
│       │   ├── features/       # 按功能模块
│       │   │   ├── studio/     # 原 index 壳
│       │   │   ├── canvas/     # 无限画布
│       │   │   ├── smart-canvas/
│       │   │   ├── assets/
│       │   │   ├── settings/
│       │   │   ├── tools/      # zimage/enhance/klein/online/angle
│       │   │   └── chat/
│       │   ├── components/ui/  # shadcn
│       │   └── lib/api/        # api-types 封装
│       └── vite.config.ts
│
├── services/
│   └── api/
│       └── src/infinite_canvas/
│           ├── main.py         # CLI 入口
│           ├── app.py          # create_app()
│           ├── core/
│           │   ├── config.py
│           │   ├── paths.py    # APP_DATA_DIR
│           │   ├── lifespan.py
│           │   └── websocket.py
│           ├── schemas/
│           ├── services/       # 业务逻辑
│           └── routes/           # 薄路由
│
├── packages/
│   ├── api-types/              # openapi-typescript 生成
│   └── canvas-schema/          # 画布 JSON 类型
│
├── tests/
│   ├── api/                    # pytest parity
│   └── e2e/                    # Playwright 14 页
│
├── reference/                  # 可选：小体积对照快照（按需）
├── workflows/                  # 内置 ComfyUI 工作流
└── docs/
    └── superpowers/specs/      # 本文件
```

> **Git 策略**：`coding/` 整目录排除出版本库；开发与 parity 测试在本地保留上游源码即可。

---

## 5. 后端迁移设计

### 5.1 策略：绞杀者拆分

1. 新建 uv 工程，`reference/main.py` 作对照
2. 导出旧版 OpenAPI 作 baseline
3. 按域拆 `routes/` + `services/`，每域加 pytest
4. **API 契约不变**：路径、请求/响应 JSON、WebSocket 消息格式与旧版一致
5. 全部 147 路由 parity 通过后，删除对 reference 的运行时依赖

### 5.2 模块拆分顺序

| 阶段 | 模块 | 路由约数 |
|------|------|----------|
| W1-2 | core, paths, websocket, upload, media | ~15 |
| W3 | canvases, projects, conversations | ~25 |
| W4 | asset_library, prompt_libraries, local_assets, shared_folders | ~35 |
| W5 | providers, config, models | ~12 |
| W6 | comfyui (instances, workflows, generate) | ~12 |
| W7 | runninghub, jimeng | ~22 |
| W8 | chat/agent/stream, canvas_video, canvas_llm, modelscope, angle, update | ~26 |

### 5.3 用户数据目录

```python
# core/paths.py
APP_DATA = Path(os.getenv("INFINITE_CANVAS_DATA", default_app_data_dir()))
DATA_DIR = APP_DATA / "data"
ASSETS_DIR = APP_DATA / "assets"
API_ENV = APP_DATA / "config" / ".env"
```

| 平台 | 默认路径 |
|------|----------|
| Windows | `%APPDATA%/infinite-canvas/` |
| macOS | `~/Library/Application Support/infinite-canvas/` |

CLI 参数：`--port`、`--host`、`--data-dir`

### 5.4 uv 工程

```toml
[project]
name = "infinite-canvas"
requires-python = ">=3.10"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "requests", "pydantic", "python-multipart", "httpx", "pillow",
]

[project.scripts]
infinite-canvas = "infinite_canvas.main:cli"
```

命令：`uv sync` · `uv run infinite-canvas` · `uv run pytest`

---

## 6. 前端迁移设计

### 6.1 页面映射（14 → React routes）

| 旧页面 | 新路由 | Feature 模块 |
|--------|--------|--------------|
| `index.html` | `/` | `features/studio` |
| `canvas-list.html` | `/canvases` | `features/canvas/list` |
| `canvas.html` | `/canvas/:id` | `features/canvas/editor` |
| `smart-canvas.html` | `/smart/:id` | `features/smart-canvas` |
| `asset-manager.html` | `/assets` | `features/assets` |
| `api-settings.html` | `/settings/api` | `features/settings/api` |
| `comfyui-settings.html` | `/settings/comfyui` | `features/settings/comfyui` |
| `gpt-chat.html` | `/chat` | `features/chat` |
| `zimage.html` | `/tools/zimage` | `features/tools/zimage` |
| `enhance.html` | `/tools/enhance` | `features/tools/enhance` |
| `klein.html` | `/tools/klein` | `features/tools/klein` |
| `online.html` | `/tools/online` | `features/tools/online` |
| `angle.html` | `/tools/angle` | `features/tools/angle` |

### 6.2 迁移顺序（由易到难）

1. **M4** Design System + App Shell + 路由
2. **M5** 设置页（api-settings, comfyui-settings）
3. **M6** 素材库 + 画布列表 + GPT 对话
4. **M7** Studio 工具页（zimage/enhance/klein/online/angle）
5. **M8** 智能画布（smart-canvas.js 行为 parity）
6. **M9** 无限画布（canvas.js 节点类型逐类迁移）

### 6.3 无限画布节点迁移

建立 **节点注册表** `packages/canvas-schema/nodes.ts`，与旧版 node type 一一对应：

- 图片 / 提示词 / API 生成 / ModelScope / ComfyUI / RunningHub / LLM / 循环 / 输出 / 视频 …
- 每个节点：React 组件 + 端口定义 + 执行 handler（调现有 API）
- 画布 JSON 格式与旧版 `data/canvases/*.json` **兼容读写**

技术：`@xyflow/react` + 自定义 Node/Edge + Zustand 存画布状态

### 6.4 Design Tokens（现代化）

```css
:root {
  --background, --foreground, --muted, --accent, --border, --radius;
}
.dark { /* 深色覆盖 */ }
```

组件：Button, Dialog, Sheet, Tabs, Command（Cmd+K 面板）, Toast, DataTable

---

## 7. Tauri 桌面端设计

### 7.1 启动流程

```
1. Tauri 启动
2. 检测单实例锁（可选第二实例唤起已有窗口）
3. spawn sidecar: infinite-canvas --port {auto} --data-dir {user}
4. 轮询 http://127.0.0.1:{port}/api/app-info 直到就绪
5. WebView 加载 apps/web（dev: Vite URL / prod: 内嵌静态）
6. 退出时 kill sidecar + 释放端口
```

### 7.2 Sidecar 打包

| 平台 | 方式 |
|------|------|
| Windows | `uv export` + PyInstaller 或 uv 冻结 venv → `infinite-canvas.exe` |
| macOS | 同上 → `infinite-canvas` 二进制，含 codesign |

Sidecar 路径通过 Tauri `externalBin` 配置。

### 7.3 桌面专属能力

| 能力 | Tauri API |
|------|-----------|
| 无边框窗口 + 自定义标题栏 | `decorations: false` |
| 系统托盘 | `tray_icon` |
| 文件选择/保存 | `@tauri-apps/plugin-dialog` |
| 深链接 | `deep-link` plugin |
| 自动更新 | v1.1+（可选 updater plugin） |

### 7.4 签名与分发

| 平台 | 要求 |
|------|------|
| Windows | Authenticode 签名（可选 SmartScreen 友好） |
| macOS | Developer ID + notarization |

---

## 8. 测试与 Parity 验收

### 8.1 自动化

| 层级 | 工具 | 目标 |
|------|------|------|
| API | pytest + httpx | 147 路由 smoke + 关键路径 |
| OpenAPI | diff baseline | schema 不 breaking |
| E2E | Playwright | 14 页手工清单自动化 |
| 画布 | 夹具 JSON | 加载旧画布 → 保存 → 再加载一致 |

### 8.2 手工 Parity 清单（14 项，全绿才发版）

1. 启动 / Studio 首页
2. 无限画布：新建、节点、连线、保存、运行
3. 智能画布：卡片、运行、@ 素材
4. API 设置：验证、拉模型
5. ComfyUI 设置：工作流测试
6. 素材库：上传、分类、裁剪
7. GPT 对话 + Agent 生图
8. ModelScope 工具页（zimage 等）
9. 队列 / 历史
10. WebSocket 多窗口同步
11. 即梦 CLI 状态
12. RunningHub 节点
13. 画布导入/导出工作流
14. 应用更新检查

### 8.3 桌面专项

- Win/macOS 安装 → 首次启动 → 创建画布 → 关闭 → 再开数据仍在
- 关窗后端口释放、无僵尸 Python
- macOS WKWebView 画布 WebGL/大列表无致命差异

---

## 9. 里程碑与周期（1 人全职）

| 里程碑 | 周期 | 交付 |
|--------|------|------|
| **M0** 基线 | W1 | OpenAPI baseline、parity 清单、reference 拷贝 |
| **M1** uv 后端壳 | W2-3 | 可启动、static 临时挂载、uv sync |
| **M2** 后端 50% | W4-6 | 一半路由拆分 + pytest |
| **M3** 后端 100% | W7-10 | 147 路由 parity、数据目录 |
| **M4** 前端 Shell | W11-13 | Design System、路由、设置页 |
| **M5** 标准页 | W14-17 | 素材、列表、chat、tools |
| **M6** 智能画布 | W18-22 | smart-canvas parity |
| **M7** 无限画布 | W23-32 | 全部节点类型 parity |
| **M8** Tauri 双端 | W33-36 | Win/macOS 安装包 |
| **M9** 全量验收 | W37-40 | E2E 全绿、发 v1.0 |

**合计：约 9～10 个月**

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| canvas.js 14k 行迁移遗漏 | 节点类型清单 + 逐类 E2E |
| macOS WebView 差异 | 真机测试；问题节点 CSS 降级 |
| 一人周期过长 | 严格里程碑，每 2 周可演示 |
| 拆分回归 | OpenAPI snapshot + pytest |
| 上游更新 | 保留 reference/，选择性 cherry-pick |
| 许可证 | 开源注明来源；商用前授权 |

---

## 11. v1.1+ 预留（不在 v1 实现）

- Agent 调度画布（Plan → DAG → Run）
- Tauri 自动更新
- Linux AppImage
- 多实例 profile

---

## 12. 审批记录

| 项 | 状态 |
|----|------|
| Tauri 2 桌面壳 | ✅ 已确认 |
| strict parity v1 | ✅ 已确认 |
| 全量 React + 现代化 UI (B+) | ✅ 默认采用 |
| uv 后端 | ✅ 已确认 |
| 仓库根目录 `ai-canvas/` | ✅ 已确认 |
| `coding/` gitignore | ✅ 已确认 |
| `AGENTS.md` / `CONTEXT.md` | ✅ 已创建（CONTEXT 为实现更新日志） |

**下一步：implementation plan（Phase 0 脚手架）。**
