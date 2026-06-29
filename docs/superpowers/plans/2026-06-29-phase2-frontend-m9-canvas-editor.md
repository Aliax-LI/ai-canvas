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

## Batch 4 缺口（待 parity）

### 节点运行 / 编排

- `runNodeCascade` 全链级联一键运行
- LTX Director 完整时间轴与子 `text` 段
- ComfyUI enhance / edit / custom workflow 全模式 UI
- RunningHub `rhParams` 完整映射
- loop 完整 `loopContext` 与级联触发下游 generator
- promptGroup 独立运行逻辑

### 画布能力

- 上游连线拖拽排序、`reorderInput`
- 端口类型校验、临时连线预览
- 节点运行队列、任务恢复
- 复制粘贴、撤销栈
- 资产库侧栏、工作流导入/导出
- 图片编辑器、PS/Chrome 插件联动
- WebSocket 多人协作
- Tauri 2 桌面打包

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
