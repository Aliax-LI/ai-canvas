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

## Batch 3 缺口（待 parity）

### 节点运行 / 编排

- 上游输入解析（连线 prompt / image refs）
- 级联执行、循环批次、Output 节点写入
- ComfyUI enhance / edit / custom workflow 全模式
- RunningHub 参数映射与 rhParams
- LTX Director 时间轴编辑与子 `text` 段
- loop / promptGroup 完整运行逻辑

### 画布能力

- 上游连线拖拽、端口类型校验、临时连线预览
- 节点运行队列、任务恢复
- 框选、多选、复制粘贴、撤销栈
- 资产库侧栏、工作流导入/导出
- 图片编辑器、PS/Chrome 插件联动
- 生成日志面板
- WebSocket 多人协作

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
