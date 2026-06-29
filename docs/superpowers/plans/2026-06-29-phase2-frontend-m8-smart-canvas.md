# Phase 2 — M8 智能画布

> **Goal:** 迁移 `smart-canvas.html` 核心卡片编辑能力至 `/smart/:id`。

## 本批交付

| 能力 | 路由 / 模块 | API |
|------|-------------|-----|
| 全屏智能画布壳 | `SmartCanvasShell` + `/smart/:id` | — |
| 加载 / 自动保存 | `features/smart-canvas/api.ts` | `GET/PUT /api/canvases/:id` |
| 四类卡片 CRUD | `SmartCard` + `CreateMenu` | 节点写入画布 JSON |
| 拖拽平移视口 | `SmartCanvasViewport` | `viewport` 字段 |
| 拖拽移动卡片 | 指针事件 | `nodes[].x/y` |
| 媒体上传卡片 | 文件选择 | `POST /api/ai/upload` |
| 分组导出（API 封装） | `exportSmartGroup` | `POST /api/smart-canvas/group-export` |

节点类型（与上游一致）：`smart-image` · `smart-prompt` · `smart-group` · `smart-loop`。

## 待 parity 补全

- 底部 Composer（引擎选择、运行、级联一键运行）
- 节点连线、端口拖拽、循环级联执行
- 资产库侧栏、工作流导入导出、图片编辑器
- 小地图、框选、快捷键、撤销栈
- 提示词模板库 / 预设、@mention 引用
- WebSocket 多人协作同步

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
