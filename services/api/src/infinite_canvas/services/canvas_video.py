"""Canvas node video generation — legacy parity (provider branches + errors)."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.schemas.canvas_ai import CanvasVideoRequest
from infinite_canvas.services import asset_ai, provider_store
from infinite_canvas.services.comfyui_generate import is_runninghub_provider
from infinite_canvas.services.jimeng import save_remote_video_to_output
from infinite_canvas.services.provider_store import is_jimeng_provider, provider_key_env

VIDEO_POLL_TIMEOUT = float(os.getenv("VIDEO_POLL_TIMEOUT", "1800"))


def video_api_root(provider: dict[str, Any]) -> str:
    base = str(provider.get("base_url") or "").strip().rstrip("/")
    if not base:
        return ""
    if asset_ai.effective_protocol(provider) == "volcengine":
        return base if base.endswith("/api/v3") else f"{base}/api/v3"
    return base if base.endswith("/v1") else f"{base}/v1"


def video_submit_url_candidates(provider: dict[str, Any], base_url: str) -> list[str]:
    root = base_url.rstrip("/")
    return [
        f"{root}/video/create",
        f"{root}/videos/generations",
        f"{root.rsplit('/v1', 1)[0]}/v2/videos/generations" if root.endswith("/v1") else f"{root}/v2/videos/generations",
    ]


def extract_task_id(raw: dict[str, Any]) -> str:
    for key in ("task_id", "id", "taskId"):
        value = raw.get(key)
        if value:
            return str(value)
    data = raw.get("data")
    if isinstance(data, dict):
        for key in ("task_id", "id", "taskId"):
            value = data.get(key)
            if value:
                return str(value)
    return ""


def video_output_urls(raw: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("video_url", "url", "output_url"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
    for container_key in ("videos", "data", "output", "outputs"):
        container = raw.get(container_key)
        if isinstance(container, list):
            for item in container:
                if isinstance(item, str) and item.strip():
                    urls.append(item.strip())
                elif isinstance(item, dict):
                    for key in ("url", "video_url", "output_url"):
                        value = item.get(key)
                        if isinstance(value, str) and value.strip():
                            urls.append(value.strip())
        elif isinstance(container, dict):
            for key in ("url", "video_url"):
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    urls.append(value.strip())
    return urls


async def canvas_video(payload: CanvasVideoRequest) -> dict[str, Any]:
    provider = provider_store.get_api_provider(payload.provider_id)
    if is_jimeng_provider(provider):
        raise HTTPException(
            status_code=501,
            detail=f"{provider.get('name') or provider['id']} 视频生成请使用即梦 CLI 端点（/api/jimeng），画布视频分支尚未完整迁移。",
        )
    if is_runninghub_provider(provider):
        raise HTTPException(
            status_code=501,
            detail="RunningHub 视频生成尚未在此迁移批次实现，请使用 OpenAI 兼容视频平台。",
        )

    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail=f"{provider.get('name') or provider['id']} 未配置 Base URL",
        )
    api_key = os.getenv(provider_key_env(provider["id"]), "")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"未配置 {provider.get('name') or provider['id']} 的 API Key，请在 API 设置中填写。",
        )

    requested_model = asset_ai.selected_model(payload.model, "veo3-fast")
    body: dict[str, Any] = {
        "prompt": payload.prompt,
        "model": requested_model,
        "duration": payload.duration,
    }
    if payload.aspect_ratio:
        body["aspect_ratio"] = payload.aspect_ratio
        body["ratio"] = payload.aspect_ratio
    if payload.resolution:
        body["resolution"] = payload.resolution
    if payload.size:
        body["size"] = payload.size

    submit_urls = video_submit_url_candidates(provider, base_url)
    headers = asset_ai.api_headers(provider=provider, model=requested_model)

    try:
        async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as client:
            raw: dict[str, Any] | None = None
            task_id = ""
            last_response: httpx.Response | None = None
            for idx, submit_url in enumerate(submit_urls):
                is_last = idx == len(submit_urls) - 1
                response = await client.post(submit_url, headers=headers, json=body)
                last_response = response
                if response.status_code >= 400:
                    if response.status_code in (404, 405) and not is_last:
                        continue
                    response.raise_for_status()
                try:
                    raw = response.json()
                    break
                except Exception:
                    if not is_last:
                        continue
                    raise HTTPException(
                        status_code=502,
                        detail=f"上游视频接口返回非 JSON 响应（状态 {response.status_code}）：{response.text[:500]}",
                    )
            if raw is None:
                status_code = last_response.status_code if last_response else 502
                text = (last_response.text if last_response else "")[:500]
                raise HTTPException(status_code=502, detail=f"上游视频接口错误：{text or status_code}")

            task_id = extract_task_id(raw) or raw.get("task_id") or raw.get("id") or ""
            result = raw
            urls = video_output_urls(result)
            if not urls and task_id:
                raise HTTPException(
                    status_code=502,
                    detail=f"视频任务已提交（task_id={task_id}），但当前迁移批次未实现轮询等待，请稍后查询上游任务。",
                )
            if not urls:
                raise HTTPException(status_code=502, detail=f"视频生成成功但没有返回视频：{result}")
            local_urls = [await save_remote_video_to_output(url) for url in urls]
            return {"videos": local_urls, "task_id": task_id, "raw": result}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"上游视频接口错误：{exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游视频接口失败：{exc}") from exc
