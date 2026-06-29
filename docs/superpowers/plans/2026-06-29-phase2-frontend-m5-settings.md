# Phase 2 — M5 设置页 Implementation Plan

> **Goal:** 迁移 `api-settings.html` 与 `comfyui-settings.html` 至 React，对接已有后端 `/api/providers` 与 `/api/comfyui/*`、`/api/workflows/*`。

**Architecture:** TanStack Query 拉取服务端状态；本地 draft 编辑 providers / workflow config；shadcn Card + 双栏 SettingsPageLayout。

**Tech Stack:** React 18 · TanStack Query · shadcn/ui · Vite proxy → FastAPI

---

## 本批交付（2026-06-29）

| 页面 | 路由 | 能力 |
|------|------|------|
| API 设置 | `/settings/api` | 平台列表、CRUD、Key（含 RH/火山）、模型列表、测试连接、拉取上游模型 |
| ComfyUI 设置 | `/settings/comfyui` | 实例地址、工作流列表、上传 JSON、暴露字段配置、保存/删除 |

## 待后续 parity 补全

- API 设置：推荐 API 卡片、RunningHub 工作流可视化编辑器、ModelScope LoRA、即梦 CLI 面板、拖拽排序
- ComfyUI：节点图预览、测试画布、运行测试、mini_cards 可视化编辑

## 验证

```bash
pnpm --filter web build
pnpm test:e2e
uv run pytest tests/api -v
```
