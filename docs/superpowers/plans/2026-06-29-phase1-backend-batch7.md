# Phase 1 Backend Batch 7 — AI 上传、画布资产与在线生图

**日期**：2026-06-29  
**范围**：Task 16–18（W8 part 1）  
**目标**：strict parity，不修改 `coding/`

## 迁移端点（15）

### Task 16 — AI upload（3）

| 方法 | 路径 | 服务 |
|------|------|------|
| POST | `/api/ai/upload` | `services/ai_upload.py` |
| POST | `/api/ai/upload-base64` | `services/ai_upload.py` |
| POST | `/api/ai/import-local-image` | `services/ai_upload.py` |

落盘：`assets/input`，复用 `output_path_for` / `output_url_for` 与 `local_assets._local_upload_kind_ext`。

### Task 17 — Canvas assets + workflows（8）

| 方法 | 路径 | 服务 |
|------|------|------|
| GET | `/api/canvas-assets` | `services/canvas_assets.py` |
| GET | `/api/smart-canvas/prompt-templates` | `services/canvas_assets.py` |
| POST | `/api/canvas-assets/check` | `services/canvas_assets.py` |
| POST | `/api/canvas-assets/download` | `services/canvas_assets.py` |
| POST | `/api/canvas-workflows/export` | `services/canvas_workflows.py` |
| POST | `/api/canvas-workflows/export-to-library` | `services/canvas_workflows.py` |
| POST | `/api/canvas-workflows/import` | `services/canvas_workflows.py` |
| POST | `/api/asset-library/workflows/upload` | `services/canvas_workflows.py` |

### Task 18 — Online image + async tasks（4）

| 方法 | 路径 | 服务 |
|------|------|------|
| POST | `/api/online-image` | `services/online_image.py` |
| POST | `/api/image-task-query` | `services/online_image.py` |
| POST | `/api/canvas-image-tasks` | `services/online_image.py` |
| GET | `/api/canvas-image-tasks/{task_id}` | `services/online_image.py` |

- OpenAI 兼容 `/v1/images/generations` 同步路径完整实现
- `CANVAS_TASKS` 复用 `comfyui_generate` 内存 dict + lock
- ModelScope / 即梦 / RunningHub / Gemini / 火山：stub 501 明确错误
- APIMart 异步轮询逻辑已移植（`wait_for_image_task`）

## 新增文件

- `services/ai_upload.py`、`canvas_assets.py`、`canvas_workflows.py`、`online_image.py`
- `routes/ai_upload.py`、`canvas_assets.py`、`online_image.py`
- `schemas/ai_upload.py`、`canvas_assets.py`、`online_image.py`
- `tests/api/test_ai_upload.py`、`test_canvas_assets.py`、`test_online_image.py`

## 验证

```bash
uv run pytest tests/api -v          # 90 passed
uv run python scripts/export_openapi_baseline.py  # 108 paths
```

## 下一步

- Batch 8：chat 域、canvas-video-tasks、或火山 volcengine 生图完整移植
