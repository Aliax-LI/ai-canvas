# Phase 2 — M9 无限画布编辑器

> **Goal:** 迁移 `canvas.html` 核心节点图编辑能力至 `/canvas/:id`。

## Batch 1（已完成）

| 能力 | 路由 / 模块 | API |
|------|-------------|-----|
| @xyflow/react 编辑器 | `features/canvas/components/CanvasFlow.tsx` | — |
| 加载 / 450ms 防抖自动保存 | `features/canvas/api.ts` | `GET/PUT /api/canvases/:id` |
| 点阵网格背景 | `Background` + `--canvas-bg` / `--canvas-grid` | `viewport` 字段 |
| 节点注册表 | `packages/canvas-schema/src/nodes.ts` | — |
| 首批 5 类节点 | `components/nodes/*` | 节点写入画布 JSON |
| 连线 | xyflow edges ↔ `connections[]` | `{id, from, to}` |
| 创建菜单 | `CreateMenu` + FAB | — |
| 顶栏整合 | `CanvasShell` + context | 标题 / 保存状态 |
| Generator 运行 | `GeneratorNode` | `POST /api/canvas-image-tasks` + poll |
| E2E | `tests/e2e/m9-canvas-editor.spec.ts` | mock canvas API |

### Batch 1 节点类型

| type | 说明 | 关键 data 字段 |
|------|------|----------------|
| `image` | 图片卡片 | `url`, `name`, `mediaKind?` |
| `prompt` | 提示词 | `text` |
| `output` | 输出 | `images[]` |
| `group` | 分组框 | `w`, `h`, `items[]` |
| `generator` | API 生图 | `apiProvider`, `model`, `ratio`, `resolution`, `inputs[]` |

## Batch 2（已完成）

| 能力 | 模块 | API |
|------|------|-----|
| 9 类 Batch 2 节点组件 | `components/nodes/*` | 见下表 |
| 未知类型降级 | `FallbackNode` + `serialize.ts` | 保留 `nodeType` + 全量 data |
| 分组创建菜单 | `CreateMenu`（基础 / 生成工作流） | — |
| API 封装 | `api.ts` | canvas-video / canvas-llm / ms/generate / canvas-comfy-tasks / runninghub |
| E2E 扩展 | `m9-canvas-editor.spec.ts` | CreateMenu + Fallback 断言 |

### Batch 2 节点类型与 API 映射

| type | 说明 | 运行 API | Batch 2 状态 |
|------|------|----------|--------------|
| `msgen` | ModelScope 生图 | `POST /api/ms/generate` | ✅ 简化运行 |
| `comfy` | ComfyUI | `POST /api/canvas-comfy-tasks` + poll | ✅ 简化运行 |
| `rh` | RunningHub | `POST /api/runninghub/submit` 或 `workflow-submit` + poll | ✅ 简化运行 |
| `video` | 视频生成 | `POST /api/canvas-video` | ✅ 简化运行 |
| `llm` | LLM 改写 | `POST /api/canvas-llm` | ✅ 简化运行 |
| `loop` | 循环控制 | — | 🟡 UI + data；运行 stub → Batch 3 |
| `text` | LTX 文本段 | — | 🟡 只读展示 |
| `ltxDirector` | LTX Director | — | 🟡 UI + data；运行 stub → Batch 3 |
| `promptGroup` | 提示词组 | — | 🟡 UI + data；运行 stub → Batch 3 |
| `fallback` | 未知类型降级 | — | ✅ JSON preview |

## Batch 3（已完成）

| 能力 | 模块 | 说明 |
|------|------|------|
| 图解析引擎 | `lib/graph.ts` | `generatorSources` / `orderedSources` / `resolveRunPayload` / `findDownstreamOutput` |
| 运行上下文 | `EditorActionsContext` + `CanvasEditorPage` | `getRunContext` / `appendLog` / `writeOutputImages` |
| 可运行节点重构 | `GeneratorNode` 等 6 类 | 上游 prompt + reference_images；写入 `generatedOutputs` 与下游 output |
| Loop 基础运行 | `LoopNode` | 串行 prompt 变体日志；作为 generator 输入源 |
| 生成日志面板 | `LogsPanel.tsx` | 右侧 Sheet；`logs[]` 持久化 |
| 画布交互 | `CanvasFlow.tsx` | 框选多选、Delete 删节点/边、`onConnect` 同步 `inputs` |
| E2E | `m9-canvas-editor.spec.ts` | prompt 预览 + 日志 toggle |

### Batch 3 节点运行状态

| type | Batch 3 状态 |
|------|--------------|
| `generator` / `msgen` / `comfy` / `video` / `rh` | ✅ 连线输入解析 + 运行 + output 写入 |
| `llm` | ✅ 上游 prompt 或 chatInput |
| `loop` | ✅ 简化串行 + 作为输入源 |
| `ltxDirector` / `promptGroup` | 🟡 仍 defer Batch 4 |

## Batch 4（已完成）

| 能力 | 模块 | 说明 |
|------|------|------|
| 统一节点运行器 | `lib/runNode.ts` | `runGeneratorNode` / `runMsGenNode` / `runComfyNode` / `runVideoNode` / `runLlmNode` / `runRhNode`；单节点与级联共用 |
| 级联引擎 | `lib/cascade.ts` | `computeCascadeOrder` / `resolveCascadeLoop` / `runNodeCascade`（serial loop）；`runStatus` / `runError` / `_cascadeIdx` |
| 撤销 / 复制粘贴 | `lib/history.ts` + `CanvasEditorPage` | `UNDO_MAX=30`；Ctrl+Z / Ctrl+Shift+Z / Ctrl+C / Ctrl+V |
| EditorActions 扩展 | `EditorActionsContext` | `runCascade` / `undo` / `redo` / `copySelected` / `paste` |
| 级联 UI | `NodeRunActions` + 工具栏 | 生成器「级联」按钮；顶栏「运行选中链」；Output / Loop 级联入口 |
| Loop 完整 context | `graph.ts` LoopContext | `{ index, total, nodeId }` 传入 `resolveRunPayload` |
| PromptGroup 运行 | `PromptGroupNode` | 聚合 preview + 下游级联 |
| Comfy / RH UI | `ComfyNode` / `RhNode` | mode select；rhParams JSON textarea |
| 资产库侧栏 | `AssetsSidebar.tsx` | `GET /api/asset-library`；点击创建 image 节点 |
| E2E | `m9-canvas-editor.spec.ts` | 级联链 mock + assets toggle + undo |

### Batch 4 defer（文档记录，不实现）

- LTX Director 完整时间轴编辑
- WebSocket 协作
- 图片编辑器、PS/Chrome 插件
- 端口类型校验、临时连线预览
- 任务恢复队列
- loop parallel 模式级联

## Batch 5 / M10 缺口（Tauri 与高级 parity）

| 项 | 说明 |
|----|------|
| **M10 Tauri 2 桌面** | sidecar 生命周期、托盘、Win/macOS 安装包 |
| 上游连线拖拽排序 | `reorderInput` |
| 工作流导入/导出 | workflow JSON |
| 节点运行队列 / 任务恢复 | 上游 queue |
| LTX Director 完整运行 | 时间轴 + text 段 |
| Comfy enhance/edit 全参数 UI | 上游完整表单 |
| RunningHub rhAppInfo 选择器 | 上游应用列表 |
| WebSocket 多人协作 | `/ws` |
| 图片编辑器 / 插件联动 | PS/Chrome |

## Batch 4 缺口（已关闭 — 见上表已完成项）

~~以下 Batch 4 原缺口已在本次交付~~

### 节点运行 / 编排（剩余 defer 见上）

### 画布能力（剩余 defer 见上）

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
