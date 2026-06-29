# Phase 2 — M6 素材库 / 画布列表 / GPT 对话

> **Goal:** 迁移 `canvas-list.html`、`asset-manager.html`（核心资产库 Tab）、`gpt-chat.html` 至 React。

## 本批交付（2026-06-29）

| 页面 | 路由 | 能力 |
|------|------|------|
| 画布列表 | `/canvases` | 项目侧栏、画布卡片、新建/删除、回收站恢复/永久删除 |
| GPT 对话 | `/chat` | 会话列表、流式 `/api/chat/stream`、模型/平台选择 |
| 素材库 | `/assets` | 资产库/分类浏览、上传（local-assets → batch add）、批量删除 |

## 待后续 parity 补全

- 画布列表：看板拖拽、剪贴板粘贴、board 平移缩放
- 素材库：提示词库/工作流/本地素材/画布资产/共享文件夹 Tabs、Avatar 注册 UI
- GPT 对话：图片模式、附件、系统提示词、分辨率选择器

## 验证

```bash
pnpm --filter web build
pnpm test:e2e
```
