"""GPT chat, agent, and streaming — legacy parity."""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from infinite_canvas.core.runtime_config import CHAT_MODEL, IMAGE_MODEL
from infinite_canvas.schemas.chat import ChatRequest
from infinite_canvas.services import asset_ai, conversations as conversation_service, online_image, provider_store
from infinite_canvas.services.online_image import generate_ai_image, image_references, save_ai_image_to_output

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "30"))
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
AI_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "1800"))
CHAT_ATTACHMENT_MAX = int(os.getenv("CHAT_ATTACHMENT_MAX", "20"))

AGENT_ACTIONS = {"chat", "generate_image", "edit_image"}
AGENT_IMAGE_KEYWORDS = [
    "生成", "画", "出图", "生图", "图片", "图像", "海报", "头像", "壁纸",
    "插画", "照片", "photo", "image", "picture", "draw", "generate",
]
AGENT_EDIT_KEYWORDS = [
    "修改", "改成", "换成", "调整", "优化", "编辑", "重绘", "上一张", "刚才",
    "这张", "那张", "参考图", "改图", "edit", "modify", "change", "revise",
]
CN_NUMERAL_MAP = {"一": 1, "二": 2, "两": 2, "俩": 2, "三": 3, "四": 4}


def chat_system_prompt(payload: ChatRequest) -> str:
    prompt = str(getattr(payload, "system_prompt", "") or "").strip()
    return prompt or SYSTEM_PROMPT


def display_title(text: str) -> str:
    title = re.sub(r"\s+", " ", text or "").strip()
    return title[:24] or "新对话"


def text_delta_from_chat_chunk(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    content = delta.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or "")
        return "".join(parts)
    return str(content) if content else ""


def sse_event(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def parse_error_payload_text(text: str) -> dict[str, Any]:
    body = str(text or "").strip()
    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def friendly_image_error_detail(text: str, size: str = "", model: str = "") -> str:
    lower_text = str(text or "").lower()
    if "invalid size" in lower_text or "invalid_value" in lower_text:
        return f"该模型不支持当前尺寸：{size or '未指定'}。请尝试更换分辨率或模型。"
    if "rate limit" in lower_text or "429" in lower_text:
        return "请求过于频繁，已被上游限流，请稍后再试。"
    if "unauthorized" in lower_text or "401" in lower_text:
        return "API Key 无效或已过期，请到「API 设置」检查 Key。"
    if "model_not_found" in lower_text or "channel not found" in lower_text:
        return f"上游平台找不到模型「{model}」可用通道。可能该模型未在此账号开通，请换一个已开通的模型。"
    return ""


def friendly_chat_error_detail(text: str, model: str = "", provider: dict[str, Any] | None = None) -> str:
    raw_text = str(text or "")
    lower_text = raw_text.lower()
    payload = parse_error_payload_text(raw_text)
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error.get("code") or payload.get("code") or "").strip()
    message = str(error.get("message") or payload.get("message") or "").strip()
    code_lc = code.lower()
    message_lc = message.lower()
    model_name = str(model or "").strip()

    if asset_ai.is_volcengine_provider(provider):
        if code_lc in {"invalidendpointormodel.notfound", "invalidendpointormodel.modelidaccessdisabled"}:
            provider_name = provider.get("name") or provider.get("id") or "火山方舟"
            return (
                f"{provider_name} 当前不接受模型名「{model_name or '未指定'}」直接调用聊天接口，"
                f"请在火山方舟控制台创建并使用推理接入点 ID（形如 `ep-...`）作为聊天模型。"
            )
        if "does not exist or you do not have access to it" in message_lc:
            return (
                f"火山方舟找不到或无权访问聊天模型「{model_name or '未指定'}」。"
                f"如果你现在填的是模型名，请改成已开通的推理接入点 ID（`ep-...`）。"
            )
    if "unauthorized" in lower_text or "401" in lower_text:
        return "API Key 无效或已过期，请到「API 设置」检查 Key。"
    if "rate limit" in lower_text or "429" in lower_text:
        return "请求过于频繁，已被上游限流，请稍后再试。"
    return ""


def chat_prompt_size_override(message: str, current_size: str = "") -> str:
    text = str(message or "")
    direct = re.search(r"(?<!\d)([1-9]\d{2,4})\s*[xX×*]\s*([1-9]\d{2,4})(?!\d)", text)
    if direct:
        width, height = int(direct.group(1)), int(direct.group(2))
        if width >= 256 and height >= 256:
            return f"{width}x{height}"
    return ""


def upstream_message_from_record(item: dict[str, Any]) -> dict[str, Any] | None:
    role = item.get("role")
    if role not in {"user", "assistant"} or item.get("type") == "image":
        return None
    attachments = item.get("attachments") or []
    if attachments and role == "user":
        from infinite_canvas.services.media_references import reference_to_data_url

        text = item.get("content", "")
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for ref in image_references(attachments[:CHAT_ATTACHMENT_MAX]):
            url = reference_to_data_url(ref)
            if url:
                content.append({"type": "image_url", "image_url": {"url": url}})
        return {"role": role, "content": content}
    return {"role": role, "content": item.get("content", "")}


def latest_chat_image_refs(conversation: dict[str, Any], limit: int = 1) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in reversed(conversation.get("messages") or []):
        url = item.get("image_url") if isinstance(item, dict) else ""
        if url:
            refs.append({"url": url, "name": item.get("content") or "上一张图片", "role": "source"})
        if len(refs) >= limit:
            break
    return refs


def image_size_from_reference(ref: dict[str, Any]) -> str:
    from infinite_canvas.core.output_files import output_file_from_url
    from PIL import Image

    path = output_file_from_url(ref.get("url", ""))
    if not path:
        return ""
    try:
        with Image.open(path) as img:
            width, height = img.size
        if width > 0 and height > 0:
            return f"{width}x{height}"
    except Exception as exc:
        print(f"[chat-agent] failed to read reference image size: {exc}")
    return ""


def chat_requested_image_count(message: str) -> int:
    text = str(message or "")
    match = re.search(r"(?<!\d)([1-4])\s*(?:张|幅|个|组|套)(?!\d)", text)
    if match:
        return max(1, min(4, int(match.group(1))))
    match = re.search(r"([一二两俩三四])\s*(?:张|幅|个|组|套)", text)
    if match:
        return max(1, min(4, CN_NUMERAL_MAP.get(match.group(1), 1)))
    return 1


def chat_split_parallel_prompts(prompt: str, count: int) -> list[str]:
    text = str(prompt or "").strip()
    if count <= 1:
        return [text]
    noun_match = re.search(r"(.+?)(?:的)?(海报|头像|壁纸|插画|照片|图片|图像)\s*$", text)
    if not noun_match:
        return [text] * count
    prefix = noun_match.group(1).strip()
    suffix = noun_match.group(2)
    prefix = re.sub(r"(?:再)?(?:生成|画|绘制|制作|创建)\s*[1-4一二两俩三四]?\s*(?:张|幅|个|组|套)?", "", prefix).strip()
    prefix = re.sub(r"[,，、\s]+$", "", prefix).strip()
    if not prefix:
        return [text] * count
    candidates = [
        item.strip(" ，,、")
        for item in re.split(r"\s*(?:和|与|、|，|,|\+|＋)\s*", prefix)
        if item.strip(" ，,、")
    ]
    if len(candidates) < count:
        return [text] * count
    return [f"{item}的{suffix}" for item in candidates[:count]]


def pick_chat_image_provider(provider_id: str = "", fallback_id: str = "") -> dict[str, Any]:
    providers = [
        p for p in provider_store.load_api_providers() if p.get("enabled", True) and (p.get("image_models") or [])
    ]
    for target in (provider_id, fallback_id):
        clean = str(target or "").strip().lower()
        if clean:
            matched = next((p for p in providers if p.get("id") == clean), None)
            if matched:
                return matched
    if providers:
        primary = next((p for p in providers if p.get("primary")), None)
        return primary or providers[0]
    return provider_store.get_api_provider(provider_id or fallback_id or "comfly")


def heuristic_agent_decision(message: str, refs: list[dict[str, Any]], has_previous_image: bool) -> dict[str, str]:
    text = str(message or "").strip().lower()
    has_image_word = any(key.lower() in text for key in AGENT_IMAGE_KEYWORDS)
    has_edit_word = any(key.lower() in text for key in AGENT_EDIT_KEYWORDS)
    if refs and (has_edit_word or has_image_word):
        return {"action": "edit_image", "prompt": message, "reply": ""}
    if has_previous_image and has_edit_word:
        return {"action": "edit_image", "prompt": message, "reply": ""}
    if has_image_word and not has_edit_word:
        return {"action": "generate_image", "prompt": message, "reply": ""}
    return {"action": "chat", "prompt": message, "reply": ""}


def parse_agent_decision(
    raw_text: str,
    message: str,
    refs: list[dict[str, Any]],
    has_previous_image: bool,
) -> dict[str, str]:
    text = str(raw_text or "").strip()
    data = None
    if text:
        match = re.search(r"\{[\s\S]*\}", text)
        candidate = match.group(0) if match else text
        try:
            data = json.loads(candidate)
        except Exception:
            data = None
    heuristic = heuristic_agent_decision(message, refs, has_previous_image)
    if not isinstance(data, dict):
        return heuristic
    action = str(data.get("action") or "").strip()
    if action not in AGENT_ACTIONS:
        action = heuristic["action"]
    prompt = str(data.get("prompt") or message).strip() or message
    reply = str(data.get("reply") or "").strip()
    if action == "edit_image" and not (refs or has_previous_image):
        action = (
            "generate_image"
            if any(key.lower() in str(message).lower() for key in AGENT_IMAGE_KEYWORDS)
            else "chat"
        )
    return {"action": action, "prompt": prompt, "reply": reply}


async def decide_chat_agent_action(
    payload: ChatRequest,
    conversation: dict[str, Any],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    has_previous_image = bool(latest_chat_image_refs(conversation, 1))
    fallback = heuristic_agent_decision(payload.message, refs, has_previous_image)
    chat_base, chat_hdrs, model = asset_ai.resolve_chat_provider(payload.provider, payload.model, payload.ms_model)
    history = conversation["messages"][-MAX_HISTORY_MESSAGES:]
    custom_system_prompt = str(getattr(payload, "system_prompt", "") or "").strip()
    system = (
        "你是图片创作聊天 Agent 的意图路由器。只返回 JSON，不要 Markdown。\n"
        "action 只能是 chat、generate_image、edit_image。\n"
        "chat: 普通问答或不需要调用图片工具。\n"
        "generate_image: 用户要求生成、绘制、创建新图片。\n"
        "edit_image: 用户要求修改参考图、上一张图、刚才生成的图，或上传了参考图并要求基于它变化。\n"
        "prompt 是交给生图/改图工具的完整中文提示词；普通聊天时也填用户原话。\n"
        "reply 是可选的短状态文本。"
    )
    upstream_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for item in history[-10:]:
        msg = upstream_message_from_record(item)
        if msg:
            upstream_messages.append(msg)
    upstream_messages.append(
        {
            "role": "user",
            "content": (
                f"当前用户输入：{payload.message}\n"
                f"用户设置的系统提示词：{custom_system_prompt or '无'}\n"
                f"本次上传参考图数量：{len(refs)}\n"
                f"对话中是否已有上一张生成图：{'是' if has_previous_image else '否'}\n"
                '请返回 JSON，例如 {"action":"generate_image","prompt":"...","reply":"..."}'
            ),
        }
    )
    try:
        provider_cfg = (
            provider_store.get_api_provider(payload.provider) if payload.provider not in ("modelscope",) else {}
        )
        async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
            req_body: dict[str, Any] = {"model": model, "messages": upstream_messages}
            if asset_ai.is_apimart_provider(provider_cfg):
                req_body["stream"] = False
            response = await client.post(
                f"{chat_base}/chat/completions",
                headers=chat_hdrs,
                json=req_body,
            )
            response.raise_for_status()
            raw = response.json()
            decision = parse_agent_decision(
                asset_ai.text_from_chat_response(raw),
                payload.message,
                refs,
                has_previous_image,
            )
            decision["router_model"] = model
            return decision
    except Exception as exc:
        print(f"[chat-agent] intent router fallback: {exc}")
        fallback["router_model"] = model
        return fallback


async def build_chat_text_reply(payload: ChatRequest, conversation: dict[str, Any]) -> dict[str, Any]:
    chat_base, chat_hdrs, model = asset_ai.resolve_chat_provider(payload.provider, payload.model, payload.ms_model)
    provider_cfg = (
        provider_store.get_api_provider(payload.provider) if payload.provider not in ("modelscope",) else {}
    )
    is_apimart = asset_ai.is_apimart_provider(provider_cfg)
    upstream_messages: list[dict[str, Any]] = [{"role": "system", "content": chat_system_prompt(payload)}]
    for item in conversation["messages"][-MAX_HISTORY_MESSAGES:]:
        msg = upstream_message_from_record(item)
        if msg:
            upstream_messages.append(msg)
    try:
        async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
            req_body: dict[str, Any] = {"model": model, "messages": upstream_messages}
            if is_apimart:
                req_body["stream"] = False
            response = await client.post(f"{chat_base}/chat/completions", headers=chat_hdrs, json=req_body)
            response.raise_for_status()
            raw = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text or ""
        friendly = friendly_chat_error_detail(body, model, provider_cfg)
        raise HTTPException(status_code=exc.response.status_code, detail=friendly or f"上游接口错误：{body}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游接口失败：{exc}") from exc
    raw_data = asset_ai.unwrap_apimart_response(raw) if isinstance(raw, dict) else raw
    return {
        "id": uuid.uuid4().hex,
        "role": "assistant",
        "content": asset_ai.text_from_chat_response(raw).strip() or "接口返回了空回复。",
        "created_at": conversation_service.now_ms(),
        "model": model,
        "raw_usage": raw_data.get("usage") if isinstance(raw_data, dict) else None,
    }


async def chat_sync(payload: ChatRequest, request: Request, x_user_id: str = "") -> dict[str, Any]:
    user_id = conversation_service.safe_user_id(x_user_id, request)
    conversation = (
        conversation_service.load_conversation(user_id, payload.conversation_id)
        if payload.conversation_id
        else conversation_service.new_conversation(user_id, display_title(payload.message))
    )
    if not conversation.get("messages"):
        conversation["title"] = display_title(payload.message)

    refs = [ref.model_dump() for ref in payload.reference_images if ref.url]
    image_refs = image_references(refs)
    user_message = {
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": payload.message,
        "created_at": conversation_service.now_ms(),
        "attachments": refs,
        "mode": payload.mode,
    }
    conversation["messages"].append(user_message)
    conversation["updated_at"] = conversation_service.now_ms()
    conversation_service.save_conversation(user_id, conversation)

    if payload.mode == "image":
        image_provider_id = payload.provider if payload.provider not in {"modelscope"} else "comfly"
        provider = provider_store.get_api_provider(image_provider_id)
        default_model = (provider.get("image_models") or [IMAGE_MODEL])[0]
        model = asset_ai.selected_model(payload.image_model or payload.model, default_model)
        image_size = chat_prompt_size_override(payload.message, payload.size) or payload.size
        try:
            image_data, raw = await generate_ai_image(
                payload.message, image_size, payload.quality, model, image_refs, provider["id"]
            )
            local_url = await save_ai_image_to_output(image_data, prefix="chat_")
        except httpx.HTTPStatusError as exc:
            text = exc.response.text or ""
            detail = friendly_image_error_detail(text, image_size, model) or f"上游生图接口错误：{text[:300]}"
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"请求上游生图接口失败：{exc}") from exc
        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "type": "image",
            "content": payload.message,
            "image_url": local_url,
            "created_at": conversation_service.now_ms(),
            "model": model,
            "size": image_size,
            "raw_usage": raw.get("usage") if isinstance(raw, dict) else None,
        }
    else:
        chat_base, chat_hdrs, model = asset_ai.resolve_chat_provider(payload.provider, payload.model, payload.ms_model)
        conv_provider = (
            provider_store.get_api_provider(payload.provider) if payload.provider not in ("modelscope",) else {}
        )
        conv_is_apimart = asset_ai.is_apimart_provider(conv_provider)
        history = conversation["messages"][-MAX_HISTORY_MESSAGES:]
        upstream_messages: list[dict[str, Any]] = [{"role": "system", "content": chat_system_prompt(payload)}]
        for item in history:
            msg = upstream_message_from_record(item)
            if msg:
                upstream_messages.append(msg)
        try:
            async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
                conv_req_body: dict[str, Any] = {"model": model, "messages": upstream_messages}
                if conv_is_apimart:
                    conv_req_body["stream"] = False
                response = await client.post(
                    f"{chat_base}/chat/completions",
                    headers=chat_hdrs,
                    json=conv_req_body,
                )
                response.raise_for_status()
                raw = response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text or ""
            friendly = friendly_chat_error_detail(body, model, conv_provider)
            raise HTTPException(status_code=exc.response.status_code, detail=friendly or f"上游接口错误：{body}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"请求上游接口失败：{exc}") from exc
        raw_data = asset_ai.unwrap_apimart_response(raw) if isinstance(raw, dict) else raw
        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "content": asset_ai.text_from_chat_response(raw).strip() or "接口返回了空回复。",
            "created_at": conversation_service.now_ms(),
            "model": model,
            "raw_usage": raw_data.get("usage") if isinstance(raw_data, dict) else None,
        }

    conversation["messages"].append(assistant_message)
    conversation["updated_at"] = conversation_service.now_ms()
    conversation_service.save_conversation(user_id, conversation)
    return {"conversation": conversation, "message": assistant_message}


async def chat_agent(payload: ChatRequest, request: Request, x_user_id: str = "") -> dict[str, Any]:
    user_id = conversation_service.safe_user_id(x_user_id, request)
    conversation = (
        conversation_service.load_conversation(user_id, payload.conversation_id)
        if payload.conversation_id
        else conversation_service.new_conversation(user_id, display_title(payload.message))
    )
    if not conversation.get("messages"):
        conversation["title"] = display_title(payload.message)

    refs = [ref.model_dump() for ref in payload.reference_images if ref.url]
    image_refs = image_references(refs)
    user_message = {
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": payload.message,
        "created_at": conversation_service.now_ms(),
        "attachments": refs,
        "mode": "agent",
    }
    conversation["messages"].append(user_message)
    conversation["updated_at"] = conversation_service.now_ms()
    conversation_service.save_conversation(user_id, conversation)

    decision = await decide_chat_agent_action(payload, conversation, image_refs)
    action = decision.get("action") or "chat"
    tool_refs = image_refs[:]
    inherited_size = ""
    if action == "edit_image" and not tool_refs:
        tool_refs = latest_chat_image_refs(conversation, 1)
        inherited_size = image_size_from_reference(tool_refs[0]) if tool_refs else ""
    if action == "edit_image" and not tool_refs:
        action = "generate_image"

    if action in {"generate_image", "edit_image"}:
        image_provider = pick_chat_image_provider(payload.image_provider or payload.provider, payload.provider)
        default_model = (image_provider.get("image_models") or [IMAGE_MODEL])[0]
        model = asset_ai.selected_model(payload.image_model or default_model, default_model)
        prompt = decision.get("prompt") or payload.message
        prompt_size = chat_prompt_size_override(payload.message, payload.size) or chat_prompt_size_override(
            prompt, payload.size
        )
        image_size = prompt_size or inherited_size or payload.size
        requested_count = 1 if action == "edit_image" else chat_requested_image_count(payload.message)
        prompts = chat_split_parallel_prompts(prompt, requested_count)
        local_urls: list[str] = []
        raw_items: list[dict[str, Any]] = []
        try:
            for item_prompt in prompts:
                image_data, raw = await generate_ai_image(
                    item_prompt, image_size, payload.quality, model, tool_refs, image_provider["id"]
                )
                local_urls.append(await save_ai_image_to_output(image_data, prefix="chat_"))
                raw_items.append(raw)
        except httpx.HTTPStatusError as exc:
            text = exc.response.text or ""
            detail = friendly_image_error_detail(text, image_size, model) or f"上游生图接口错误：{text[:300]}"
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"请求上游生图接口失败：{exc}") from exc
        local_url = local_urls[0] if local_urls else ""
        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "type": "image",
            "content": prompt,
            "image_url": local_url,
            "image_urls": local_urls,
            "created_at": conversation_service.now_ms(),
            "model": model,
            "provider": image_provider["id"],
            "size": image_size,
            "image_count": len(local_urls),
            "prompts": prompts,
            "agent_action": action,
            "agent_reply": decision.get("reply") or "",
            "used_references": tool_refs,
            "raw_usage": raw_items[0].get("usage") if raw_items and isinstance(raw_items[0], dict) else None,
        }
    else:
        assistant_message = await build_chat_text_reply(payload, conversation)
        assistant_message["agent_action"] = "chat"

    conversation["messages"].append(assistant_message)
    conversation["updated_at"] = conversation_service.now_ms()
    conversation_service.save_conversation(user_id, conversation)
    return {
        "conversation": conversation,
        "message": assistant_message,
        "agent": {"action": action, "decision": decision},
    }


async def chat_stream(payload: ChatRequest, request: Request, x_user_id: str = "") -> StreamingResponse:
    if payload.mode == "image":
        raise HTTPException(status_code=400, detail="图片模式请使用 /api/chat")

    user_id = conversation_service.safe_user_id(x_user_id, request)
    conversation = (
        conversation_service.load_conversation(user_id, payload.conversation_id)
        if payload.conversation_id
        else conversation_service.new_conversation(user_id, display_title(payload.message))
    )
    if not conversation.get("messages"):
        conversation["title"] = display_title(payload.message)

    refs = [ref.model_dump() for ref in payload.reference_images if ref.url]
    user_message = {
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": payload.message,
        "created_at": conversation_service.now_ms(),
        "attachments": refs,
        "mode": payload.mode,
    }
    conversation["messages"].append(user_message)
    conversation["updated_at"] = conversation_service.now_ms()
    conversation_service.save_conversation(user_id, conversation)

    chat_base, chat_hdrs, model = asset_ai.resolve_chat_provider(payload.provider, payload.model, payload.ms_model)
    stream_provider = (
        provider_store.get_api_provider(payload.provider) if payload.provider not in ("modelscope",) else {}
    )
    history = conversation["messages"][-MAX_HISTORY_MESSAGES:]
    upstream_messages: list[dict[str, Any]] = [{"role": "system", "content": chat_system_prompt(payload)}]
    for item in history:
        msg = upstream_message_from_record(item)
        if msg:
            upstream_messages.append(msg)

    async def stream():
        content_parts: list[str] = []
        raw_usage = None
        yield sse_event({"type": "meta", "conversation": conversation})
        try:
            async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{chat_base}/chat/completions",
                    headers=chat_hdrs,
                    json={"model": model, "messages": upstream_messages, "stream": True},
                ) as response:
                    if response.status_code >= 400:
                        detail = await response.aread()
                        body = detail.decode("utf-8", errors="ignore")
                        friendly = friendly_chat_error_detail(body, model, stream_provider)
                        yield sse_event({"type": "error", "detail": friendly or f"上游接口错误：{body}"})
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line[5:].strip()
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(chunk, dict) and chunk.get("usage"):
                            raw_usage = chunk.get("usage")
                        delta = text_delta_from_chat_chunk(chunk)
                        if delta:
                            content_parts.append(delta)
                            yield sse_event({"type": "delta", "delta": delta})
        except httpx.HTTPError as exc:
            yield sse_event({"type": "error", "detail": f"请求上游接口失败：{exc}"})
            return

        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "content": "".join(content_parts).strip() or "接口返回了空回复。",
            "created_at": conversation_service.now_ms(),
            "model": model,
            "raw_usage": raw_usage,
        }
        conversation["messages"].append(assistant_message)
        conversation["updated_at"] = conversation_service.now_ms()
        conversation_service.save_conversation(user_id, conversation)
        yield sse_event({"type": "done", "conversation": conversation, "message": assistant_message})

    return StreamingResponse(stream(), media_type="text/event-stream")
