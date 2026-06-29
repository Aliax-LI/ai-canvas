# Phase 2 — M9 无限画布编辑器（Batch 1）

> **Goal:** 迁移 `canvas.html` 核心节点图编辑能力至 `/canvas/:id`（基础设施 + 首批 5 类节点）。

## 本批交付

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

### Batch 1 节点类型（已实现）

| type | 说明 | 关键 data 字段 |
|------|------|----------------|
| `image` | 图片卡片 | `url`, `name`, `mediaKind?` |
| `prompt` | 提示词 | `text` |
| `output` | 输出 | `images[]` |
| `group` | 分组框 | `w`, `h`, `items[]` |
| `generator` | API 生图 | `apiProvider`, `model`, `ratio`, `resolution`, `inputs[]` |

## 待 parity 补全（后续批次）

### 节点类型

- `msgen` — ModelScope 云端生图
- `comfy` — ComfyUI 工作流节点
- `rh` — RunningHub
- `video` — 视频生成
- `llm` — LLM 提示词改写
- `loop` — 循环控制
- `text` — 纯文本节点
- `ltxDirector` — LTX Director
- `promptGroup` — 提示词组

### 画布能力

- 上游连线拖拽、端口类型校验、临时连线预览
- 节点运行队列、级联执行、循环批次
- 框选、多选、复制粘贴、撤销栈
- 资产库侧栏、工作流导入/导出
- 图片编辑器、PS/Chrome 插件联动
- 生成日志面板、任务恢复
- WebSocket 多人协作
- 未知节点类型的降级渲染（加载旧 JSON 不丢数据）

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
