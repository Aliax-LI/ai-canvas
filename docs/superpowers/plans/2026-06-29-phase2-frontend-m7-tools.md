# Phase 2 — M7 Studio 工具页

> **Goal:** 迁移 `zimage` / `enhance` / `klein` / `online` / `angle` 五个 Studio 工具页。

## 本批交付

| 页面 | 路由 | API |
|------|------|-----|
| 文生图 | `/tools/zimage` | `/api/generate`（本地）、`/generate`（云端 MS） |
| 细节增强 | `/tools/enhance` | ComfyUI Enhance / `/api/ms/generate` |
| 图片编辑 | `/tools/klein` | Flux2-Klein / MS Klein |
| 在线生图 | `/tools/online` | `/api/online-image` + 参考图 upload |
| 角度控制 | `/tools/angle` | `/api/angle/generate` + poll |

共享：`ToolLayout`、`HistoryMasonry`、`features/tools/api.ts`；Vite 代理 `/generate`。

## 待 parity 补全

- 历史批量管理、lightbox、Three.js 角度 3D 预览
- enhance 二阶段 upscale、klein LoRA 开关
- zimage 引擎切换动画与 masonry 无限滚动

## 验证

```bash
pnpm --filter web build && pnpm test:e2e
```
