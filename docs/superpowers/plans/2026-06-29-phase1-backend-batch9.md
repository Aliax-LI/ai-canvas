# Phase 1 Batch 9 — Avatar / 多平台生图 / Canvas Video 完整迁移

## 目标

消除后端最后一批 501 stub，与 `coding/Infinite-Canvas/main.py` strict parity。

## 迁移项

| 模块 | 源（legacy） | 目标 |
|------|-------------|------|
| Avatar 注册 | `register_asset_library_avatar` / `check_asset_library_avatar` | `services/avatar.py` + APIMart/Volcengine 资产 API |
| 多平台生图 | `generate_*_provider_image` ×5 | `provider_image.py` + `jimeng_generate.py` + `runninghub_provider.py` |
| Canvas 视频 | `canvas_video` 全分支 | `canvas_video.py`（即梦/RunningHub/APIMart/火山/Agnes/玉玉 + 轮询） |

## 新增服务文件

- `provider_helpers.py` — 尺寸/视频 URL/任务状态 helper
- `apimart_media.py` — APIMart 上传与校验
- `volcengine_assets.py` — 火山 Ark 资产 API + 视频媒体引用
- `avatar.py` — 资产库数字人注册路由逻辑
- `jimeng_generate.py` — 即梦 provider 生图/生视频
- `runninghub_provider.py` — RunningHub OpenAPI 生图/生视频
- `provider_image.py` — ModelScope/Gemini/火山生图
- `video_tasks.py` — 视频任务轮询、Agnes/Yuli 分支

## 验证

```bash
uv run pytest tests/api -v          # 106 passed
uv run python scripts/export_openapi_baseline.py  # 126 paths
rg '501|尚未迁移' services/           # 无匹配
```

## 测试更新

- `test_asset_library_crud.py` — avatar mock happy path
- `test_online_image.py` — ModelScope provider mock
- `test_canvas_ai.py` — 即梦/RunningHub 视频 mock
