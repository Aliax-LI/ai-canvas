"""Canvas node LLM — legacy parity."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.schemas.canvas_ai import CanvasLLMRequest
from infinite_canvas.services import asset_ai, provider_store
from infinite_canvas.services.media_references import (
    is_image_reference_value,
    is_video_reference_value,
    media_reference_to_url,
    video_reference_to_frame_data_urls,
)

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "30"))
AI_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "1800"))


async def canvas_llm(payload: CanvasLLMRequest) -> dict[str, Any]:
    chat_base, chat_hdrs, model = asset_ai.resolve_chat_provider(payload.provider, payload.model, payload.ms_model)
    llm_provider = provider_store.get_api_provider(payload.provider) if payload.provider not in ("modelscope",) else {}
    is_apimart = asset_ai.is_apimart_provider(llm_provider)
    system_prompt = (payload.system_prompt or "").strip()
    upstream_messages: list[dict[str, Any]] = (
        [{"role": "system", "content": system_prompt}] if system_prompt else []
    )
    for item in payload.messages[-MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            upstream_messages.append({"role": role, "content": content})

    image_inputs = [img for img in (payload.images or []) if is_image_reference_value(img)]
    video_inputs = [video for video in (payload.videos or []) if is_video_reference_value(video)]
    if image_inputs or video_inputs:
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": payload.message}]
        ok_imgs = 0
        for img in image_inputs[:8]:
            ref_url = media_reference_to_url(img, max_image_size=1024)
            if not ref_url:
                continue
            content_parts.append({"type": "image_url", "image_url": {"url": ref_url}})
            ok_imgs += 1
        ok_videos = 0
        for video in video_inputs[:3]:
            frame_urls = await video_reference_to_frame_data_urls(video, max_frames=6, max_size=768)
            if frame_urls:
                ok_videos += 1
                content_parts.append(
                    {
                        "type": "text",
                        "text": f"以下是视频 {ok_videos} 按时间顺序抽取的关键帧，请结合这些画面理解视频内容。",
                    }
                )
                for frame_url in frame_urls:
                    content_parts.append({"type": "image_url", "image_url": {"url": frame_url}})
            else:
                ref_url = media_reference_to_url(video)
                if not ref_url:
                    continue
                content_parts.append({"type": "video_url", "video_url": {"url": ref_url}})
                ok_videos += 1
        upstream_messages.append({"role": "user", "content": content_parts})
    else:
        upstream_messages.append({"role": "user", "content": payload.message})

    raw: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
            req_body: dict[str, Any] = {"model": model, "messages": upstream_messages}
            if is_apimart:
                req_body["stream"] = False
            response = await client.post(
                f"{chat_base}/chat/completions",
                headers=chat_hdrs,
                json=req_body,
            )
            response.raise_for_status()
            if not response.content:
                raise HTTPException(status_code=502, detail="上游接口返回了空响应")
            raw = response.json()
    except httpx.HTTPStatusError as exc:
        from infinite_canvas.services.chat import friendly_chat_error_detail

        body = exc.response.text or ""
        friendly = friendly_chat_error_detail(body, model, llm_provider)
        raise HTTPException(status_code=exc.response.status_code, detail=friendly or f"上游接口错误：{body}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游接口失败：{exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"解析上游响应失败：{exc}") from exc

    try:
        text = asset_ai.text_from_chat_response(raw).strip() if isinstance(raw, dict) else ""
        text = text or "接口返回了空回复。"
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"解析回复内容失败：{exc}") from exc
    raw_data = asset_ai.unwrap_apimart_response(raw) if isinstance(raw, dict) else {}
    return {"text": text, "model": model, "raw_usage": raw_data.get("usage")}
