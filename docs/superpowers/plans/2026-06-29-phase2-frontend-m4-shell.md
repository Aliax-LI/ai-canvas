# Phase 2 — M4 前端 Design System 与 App Shell

**日期**: 2026-06-29  
**状态**: 已完成  
**前置**: M2–M3 后端 126 API paths parity

---

## 目标

搭建 pnpm monorepo + React SPA 脚手架，交付产品型 B+ App Shell、14 页路由占位、Design Token、共享 packages 与 E2E happy path。

## 交付清单

| 项 | 路径 | 状态 |
|----|------|------|
| pnpm workspace 根 | `package.json`, `pnpm-workspace.yaml` | ✅ |
| React + Vite + Tailwind + shadcn | `apps/web/` | ✅ |
| Design Token | `apps/web/src/styles/tokens.css` | ✅ |
| 产品型 Shell | `apps/web/src/components/shell/ProductShell.tsx` | ✅ |
| 工具型 Canvas Shell stub | `apps/web/src/components/shell/CanvasShell.tsx` | ✅ |
| 14 页路由占位 | `apps/web/src/features/*`, `apps/web/src/app/router.tsx` | ✅ |
| api-types | `packages/api-types/` | ✅ |
| canvas-schema stub | `packages/canvas-schema/` | ✅ |
| Vite 代理 | `apps/web/vite.config.ts` | ✅ |
| Playwright E2E | `tests/e2e/app-shell.spec.ts` | ✅ |

## 路由表

| 路由 | Feature |
|------|---------|
| `/` | studio home |
| `/canvases` | canvas list |
| `/canvas/:id` | canvas editor（工具型 Shell） |
| `/smart/:id` | smart canvas |
| `/assets` | assets |
| `/settings/api` | api settings |
| `/settings/comfyui` | comfyui settings |
| `/chat` | chat |
| `/tools/*` | zimage / enhance / klein / online / angle |

## 验证

```bash
pnpm install
pnpm --filter web build
pnpm --filter e2e test
```

## 下一步

- M4 续：设置页（API / ComfyUI）业务迁移
- 素材库、聊天、tools 页逐批 parity
- 画布节点注册表填充 `packages/canvas-schema`
