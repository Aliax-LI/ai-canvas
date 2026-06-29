"""Canvas node video generation — legacy parity (all provider branches)."""

from __future__ import annotations

import os
import re
import urllib.parse

import httpx
from fastapi import HTTPException

from infinite_canvas.schemas.canvas_ai import CanvasVideoRequest
from infinite_canvas.services import asset_ai, provider_store
from infinite_canvas.services.apimart_media import (
    apimart_veo31_aspect,
    apimart_veo31_duration,
    apimart_veo31_model,
    apimart_veo31_resolution,
    apimart_video_duration,
    apimart_video_reference_error,
    apimart_video_size,
    apply_trusted_asset_prompt_index,
    invalid_video_image_preview,
    is_apimart_veo31_model,
    upload_audio_for_apimart,
    upload_image_for_apimart,
    upload_video_for_apimart,
    valid_apimart_video_image_input,
)
from infinite_canvas.services.comfyui_generate import is_runninghub_provider
from infinite_canvas.services.jimeng import save_remote_video_to_output
from infinite_canvas.services.jimeng_generate import generate_jimeng_video
from infinite_canvas.services.media_references import reference_to_data_url
from infinite_canvas.services.online_image import extract_task_id
from infinite_canvas.services.provider_helpers import (
    VIDEO_POLL_TIMEOUT,
    is_agnes_provider,
    is_yuli_provider,
    looks_like_html_response,
    video_api_root,
    video_output_urls,
    video_submit_url_candidates,
)
from infinite_canvas.services.provider_store import is_jimeng_provider, provider_key_env
from infinite_canvas.services.runninghub_provider import generate_runninghub_video
from infinite_canvas.services.video_tasks import generate_agnes_video, generate_yuli_openai_video, wait_for_video_task
from infinite_canvas.services.volcengine_assets import (
    looks_like_image_media_url,
    probe_local_audio_duration_seconds,
    volcengine_content_role,
    volcengine_media_reference_url,
    volcengine_video_duration,
    volcengine_video_reference_content_items,
    volcengine_video_resolution,
)

async def canvas_video(payload: CanvasVideoRequest):
    provider = provider_store.get_api_provider(payload.provider_id)
    if provider_store.is_jimeng_provider(provider):
        return await generate_jimeng_video(payload, provider)
    if is_runninghub_provider(provider):
        try:
            return await generate_runninghub_video(payload, provider)
        except httpx.HTTPStatusError as exc:
            text = exc.response.text
            raise HTTPException(status_code=exc.response.status_code, detail=f"RunningHub 视频接口错误：{text}") from exc
        except httpx.HTTPError as exc:
            # log_net_error(f"视频(RunningHub) 网络/TLS错误 model={payload.model}", exc)
            raise HTTPException(status_code=502, detail=f"请求 RunningHub 视频接口失败：{exc}") from exc
    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    api_key = os.getenv(provider_store.provider_key_env(provider["id"]), "")
    if not api_key:
        raise HTTPException(status_code=400, detail=f"未配置 {provider.get('name') or provider['id']} 的 API Key，请在 API 设置中填写。")
    is_apimart = asset_ai.is_apimart_provider(provider)
    is_volcengine = asset_ai.is_volcengine_provider(provider)
    is_yuli = is_yuli_provider(provider)
    is_agnes = is_agnes_provider(provider, payload.model)
    volc_is_proxy = bool(is_volcengine and urllib.parse.urlparse(base_url).path.rstrip("/"))
    submit_urls = video_submit_url_candidates(provider, base_url)
    submit_url = submit_urls[0]
    requested_model = asset_ai.selected_model(payload.model, "agnes-video-v2.0" if is_agnes else "veo3-fast")
    is_veo31 = is_apimart and is_apimart_veo31_model(requested_model)
    if is_agnes:
        try:
            async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as agnes_client:
                return await generate_agnes_video(agnes_client, payload, provider, base_url, requested_model)
        except httpx.HTTPStatusError as exc:
            text = exc.response.text
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agnes 视频接口错误：{text}") from exc
        except httpx.HTTPError as exc:
            # log_net_error(f"视频(Agnes) 网络/TLS错误 model={requested_model}", exc)
            raise HTTPException(status_code=502, detail=f"请求 Agnes 视频接口失败：{exc}") from exc
    # 玉玉API veo3.1 走 OpenAI multipart 格式（支持 seconds 时长）；其余模型（doubao 等）
    # 沿用下方原生 /v1/video/create JSON 流程。
    if is_yuli and yuli_is_veo_openai_model(requested_model):
        try:
            async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as yuli_client:
                return await generate_yuli_openai_video(yuli_client, payload, provider, base_url, requested_model)
        except httpx.HTTPStatusError as exc:
            text = exc.response.text
            raise HTTPException(status_code=exc.response.status_code, detail=f"上游视频接口错误：{text}") from exc
        except httpx.HTTPError as exc:
            # log_net_error(f"视频(玉玉) 网络/TLS错误 model={requested_model}", exc)
            raise HTTPException(status_code=502, detail=f"请求上游视频接口失败：{exc}") from exc
    try:
        async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as client:
            # --- 构造图片载荷 ---
            if is_apimart:
                # APIMart 只接受 http/https 或 asset:// URL，先上传本地图片取回网络 URL
                image_with_roles = []
                invalid_images = []  # 每项为 (原始 URL, 失败原因)
                video_payload = []
                invalid_videos = []
                for ref_url in payload.videos[:3]:
                    ref_url = str(ref_url or "").strip()
                    if not ref_url:
                        continue
                    normalized_video_url = await upload_video_for_apimart(client, provider, ref_url)
                    if valid_apimart_video_image_input(normalized_video_url):
                        video_payload.append(normalized_video_url)
                    else:
                        reason = normalized_video_url[4:] if isinstance(normalized_video_url, str) and normalized_video_url.startswith("ERR:") else apimart_video_reference_error(ref_url)
                        invalid_videos.append((ref_url, reason))
                if invalid_videos:
                    first_url, first_reason = invalid_videos[0]
                    sample = invalid_video_image_preview(first_url)
                    raise HTTPException(
                        status_code=400,
                        detail=f"输入视频无法转换为 APIMart 支持的格式：{sample}\n原因：{first_reason}"
                    )
                apimart_model = apimart_veo31_model(requested_model) if is_veo31 else ""
                if apimart_model == "veo3.1-lite" and payload.images:
                    raise HTTPException(status_code=400, detail="veo3.1-lite 不支持图片输入，请改用 veo3.1-fast 或 veo3.1-quality。")
                image_limit = 0 if apimart_model == "veo3.1-lite" else (3 if is_veo31 else 9)
                for ref in payload.images[:image_limit]:
                    if not ref.url:
                        continue
                    role = str(ref.role or "").strip()
                    if not is_veo31 and role in {"first_frame", "last_frame", "reference_image"}:
                        up_url = await upload_image_for_apimart(client, provider, ref.url)
                        if valid_apimart_video_image_input(up_url):
                            image_with_roles.append({"url": up_url, "role": role})
                        else:
                            reason = up_url[4:] if isinstance(up_url, str) and up_url.startswith("ERR:") else "未知错误"
                            invalid_images.append((ref.url, reason))
                image_payload = []
                if not image_with_roles:
                    for ref in payload.images[:image_limit]:
                        if not ref.url:
                            continue
                        up_url = await upload_image_for_apimart(client, provider, ref.url)
                        if valid_apimart_video_image_input(up_url):
                            image_payload.append(up_url)
                        else:
                            reason = up_url[4:] if isinstance(up_url, str) and up_url.startswith("ERR:") else "未知错误"
                            invalid_images.append((ref.url, reason))
                if payload.images and not image_with_roles and not image_payload:
                    first_url, first_reason = invalid_images[0] if invalid_images else ("", "未知错误")
                    sample = invalid_video_image_preview(first_url)
                    raise HTTPException(status_code=400, detail=f"输入图片无法转换为视频接口支持的格式：{sample}\n原因：{first_reason}\n请确认本地文件存在且不超过 10MB；VEO3.1 需要图片是 APIMart 可访问的 http/https / asset:// / data URL。")
                # --- APIMart 请求体 ---
                if is_veo31:
                    model = apimart_model
                    body = {
                        "prompt": payload.prompt,
                        "model": model,
                        "duration": apimart_veo31_duration(payload.duration),
                        "aspect_ratio": apimart_veo31_aspect(payload.aspect_ratio),
                        "resolution": apimart_veo31_resolution(payload.resolution),
                    }
                    if image_payload and model != "veo3.1-lite":
                        video_images = image_payload[:3]
                        if model == "veo3.1-quality" and len(video_images) > 2:
                            video_images = video_images[:2]
                        body["image_urls"] = video_images
                        if len(video_images) == 2:
                            body["generation_type"] = "frame"
                        elif len(video_images) >= 3 and model != "veo3.1-quality":
                            body["generation_type"] = "reference"
                    if model != "veo3.1-lite":
                        body["official_fallback"] = False
                else:
                    body = {
                        "prompt": payload.prompt,
                        "model": asset_ai.selected_model(payload.model, "doubao-seedance-2.0"),
                        "duration": apimart_video_duration(payload.duration),
                        "size": apimart_video_size(payload.aspect_ratio or payload.size),
                        "resolution": payload.resolution or "480p",
                    }
                    if image_with_roles and video_payload:
                        raise HTTPException(status_code=400, detail="APIMart Seedance 的 image_with_roles 不能和 video_urls 同时使用，请只保留图片首尾帧或参考视频其中一种。")
                    if image_with_roles:
                        body["image_with_roles"] = image_with_roles
                    elif image_payload:
                        body["image_urls"] = image_payload[:9]
                    if video_payload:
                        body["video_urls"] = video_payload
                    audio_payload = []
                    invalid_audios = []
                    for ref_url in (payload.audios or [])[:3]:
                        ref_url = str(ref_url or "").strip()
                        if not ref_url:
                            continue
                        normalized_audio_url = await upload_audio_for_apimart(client, provider, ref_url)
                        if valid_apimart_video_image_input(normalized_audio_url):
                            audio_payload.append(normalized_audio_url)
                        else:
                            reason = normalized_audio_url[4:] if isinstance(normalized_audio_url, str) and normalized_audio_url.startswith("ERR:") else "未知错误"
                            invalid_audios.append((ref_url, reason))
                    if invalid_audios:
                        first_url, first_reason = invalid_audios[0]
                        raise HTTPException(status_code=400, detail=f"参考音频无法转换为 APIMart 支持的地址：{invalid_video_image_preview(first_url)}\n原因：{first_reason}")
                    if audio_payload:
                        body["audio_urls"] = audio_payload
                    if payload.trusted_asset:
                        img_count = len(body.get("image_urls") or []) or len(image_with_roles)
                        body["prompt"] = apply_trusted_asset_prompt_index(
                            body["prompt"], img_count, len(video_payload), len(audio_payload)
                        )
                    if payload.seed is not None:
                        body["seed"] = payload.seed
                    if payload.return_last_frame:
                        body["return_last_frame"] = True
                    if payload.generate_audio:
                        body["generate_audio"] = True
            else:
                # 非 APIMart：data URL 方式（OpenAI / ComflyAI 接口）
                if is_volcengine and not volc_is_proxy:
                    text = str(payload.prompt or "").strip()
                    volc_model = asset_ai.selected_model(payload.model, "doubao-seedance-2-0-fast-260128")
                    body = {
                        "model": volc_model,
                        "content": [
                            {
                                "type": "text",
                                "text": text,
                            }
                        ],
                    }
                    # 火山方舟视频接口（含 Seedance 2.0 图生视频）均通过 body 的 duration 字段控制时长；
                    # 之前对 seedance-2.0 + 参考图的情况省略了 duration，导致接口回退到默认 5s。
                    body["duration"] = volcengine_video_duration(payload.duration)
                    if payload.aspect_ratio:
                        body["ratio"] = payload.aspect_ratio
                    resolution = volcengine_video_resolution(payload.resolution)
                    if resolution:
                        body["resolution"] = resolution
                    if payload.watermark:
                        body["watermark"] = True
                    if payload.generate_audio:
                        body["generate_audio"] = True
                    if payload.camerafixed:
                        body["camerafixed"] = True
                    image_like_urls = set()
                    frame_roles_used = {"first_frame": False, "last_frame": False}
                    volc_video_count = 0

                    def append_volcengine_image(url: str, role: str):
                        if role in {"first_frame", "last_frame"}:
                            if frame_roles_used.get(role):
                                return False
                            frame_roles_used[role] = True
                        elif role != "reference_image":
                            return False
                        body["content"].append({
                            "type": "image_url",
                            "image_url": {"url": url},
                            "role": role,
                        })
                        image_like_urls.add(url)
                        return True

                    for ref in payload.images[:9]:
                        url = volcengine_media_reference_url(ref.url, max_image_size=1536)
                        if not url:
                            continue
                        role = volcengine_content_role(ref.role, "image")
                        if role in {"first_frame", "last_frame"}:
                            append_volcengine_image(url, role)
                        elif payload.multimodal:
                            # 智能多帧/多参模式：多张图作为参考图提交，不能全部伪装成首帧。
                            append_volcengine_image(url, "reference_image")
                        elif not frame_roles_used["first_frame"]:
                            # 普通图生视频没有显式 role 时，只取第一张作为首帧。
                            append_volcengine_image(url, "first_frame")
                    for url in (payload.videos or [])[:3]:
                        text_url = str(url or "").strip()
                        if not text_url:
                            continue
                        media_url = volcengine_media_reference_url(text_url, max_image_size=1536 if looks_like_image_media_url(text_url) else None)
                        if not media_url:
                            continue
                        if media_url in image_like_urls or looks_like_image_media_url(media_url):
                            append_volcengine_image(media_url, "reference_image" if payload.multimodal else "first_frame")
                            continue
                        video_items = await volcengine_video_reference_content_items(media_url)
                        body["content"].extend(video_items)
                        volc_video_count += 1
                    for url in (payload.audios or [])[:3]:
                        duration = probe_local_audio_duration_seconds(url)
                        if duration is not None and (duration < 1.8 or duration > 15.2):
                            raise HTTPException(
                                status_code=400,
                                detail=f"参考音频时长 {duration:.2f} 秒超出范围：方舟 Seedance 参考音频要求在 1.8 ~ 15.2 秒之间，请裁剪后再插入。"
                            )
                        audio_url = volcengine_media_reference_url(url, max_image_size=None)
                        if not audio_url:
                            continue
                        body["content"].append({
                            "type": "audio_url",
                            "audio_url": {"url": audio_url},
                            "role": volcengine_content_role("", "audio"),
                        })
                    if payload.trusted_asset and body["content"] and body["content"][0].get("type") == "text":
                        body["content"][0]["text"] = apply_trusted_asset_prompt_index(
                            body["content"][0].get("text") or "", len(image_like_urls), volc_video_count, 0
                        )
                    if payload.seed is not None:
                        body["seed"] = payload.seed
                elif is_yuli:
                    # 玉玉API（yuli.host）视频走自有 veo 统一格式：POST /v1/video/create。
                    # 字段：model / prompt / images[]（http(s) URL）/ enhance_prompt /
                    # enable_upsample / aspect_ratio（仅 16:9、9:16）。无 duration 字段，
                    # 时长由模型本身决定，所以这里不传 duration/seconds。
                    yuli_images = []
                    for ref in payload.images[:3]:
                        ref_url = str(getattr(ref, "url", "") or "").strip()
                        if not ref_url:
                            continue
                        if ref_url.startswith("http://") or ref_url.startswith("https://"):
                            yuli_images.append(ref_url)
                        else:
                            # 本地/dataURL 图片转成 data URL 兜底传递
                            data_url = reference_to_data_url(ref.dict(), max_size=1536)
                            if data_url:
                                yuli_images.append(data_url)
                    prompt_text = str(payload.prompt or "")
                    # veo 只支持英文提示词：仅在含中文等非 ASCII 字符时才开启翻译增强，
                    # 纯英文原样传递（避免增强改写时引入人物等触发安全过滤的描述）。
                    needs_enhance = any(ord(ch) > 127 for ch in prompt_text)
                    body = {
                        "model": asset_ai.selected_model(payload.model, "veo3.1-fast"),
                        "prompt": prompt_text,
                        "enhance_prompt": needs_enhance,
                    }
                    if yuli_images:
                        body["images"] = yuli_images
                    ratio = str(payload.aspect_ratio or "").strip()
                    if ratio in {"16:9", "9:16"}:
                        body["aspect_ratio"] = ratio
                    if payload.enable_upsample:
                        body["enable_upsample"] = True
                else:
                    image_payload = []
                    for ref in payload.images[:4]:
                        if ref.url:
                            image_payload.append(reference_to_data_url(ref.dict(), max_size=1536))
                    body = {
                        "prompt": payload.prompt,
                        "model": asset_ai.selected_model(payload.model, "veo3-fast"),
                        "duration": payload.duration,
                        "watermark": payload.watermark,
                    }
                    if payload.aspect_ratio:
                        body["aspect_ratio"] = payload.aspect_ratio
                        body["ratio"] = payload.aspect_ratio
                    if payload.size:
                        body["size"] = payload.size
                    if payload.resolution:
                        body["resolution"] = payload.resolution
                    if image_payload:
                        body["images"] = image_payload
                    if payload.videos:
                        body["videos"] = [v for v in payload.videos if v]
                    if payload.enhance_prompt:
                        body["enhance_prompt"] = True
                    if payload.enable_upsample:
                        body["enable_upsample"] = True
                    if payload.seed is not None:
                        body["seed"] = payload.seed
                    if payload.camerafixed:
                        body["camerafixed"] = True
                    if payload.return_last_frame:
                        body["return_last_frame"] = True
                    if payload.generate_audio:
                        body["generate_audio"] = True
            # --- 发起视频生成请求 ---
            raw = None
            html_response = None
            last_response = None
            last_json_error = None
            total_candidates = len(submit_urls)
            for idx, candidate_url in enumerate(submit_urls):
                submit_url = candidate_url
                is_last = idx == total_candidates - 1
                response = await client.post(submit_url, headers=asset_ai.api_headers(provider=provider), json=body)
                last_response = response
                if response.status_code >= 400:
                    # 404/405（或直接返回网页 HTML）通常表示该平台不支持这个端点路径——
                    # 例如有的站点只实现了统一格式的 /v2/videos/generations，而我们先试了 /v1。
                    # 这种情况要继续尝试下一个候选端点（关键修复：以前在这里直接 raise_for_status，
                    # 第一个 /v1 报错就抛出，永远轮不到 /v2，表现为“接口错误”）。
                    # 其它错误（模型不支持/时长/额度等请求被拒）说明端点是存在的，直接抛出交给外层友好提示。
                    endpoint_missing = response.status_code in (404, 405) or looks_like_html_response(response.text)
                    if endpoint_missing and not is_last:
                        continue
                    response.raise_for_status()
                try:
                    raw = response.json()
                    break
                except Exception as exc:
                    last_json_error = exc
                    if looks_like_html_response(response.text):
                        html_response = response
                        continue
                    if not is_last:
                        continue
                    resp_text = response.text[:500]
                    raise HTTPException(status_code=502, detail=f"上游视频接口返回非 JSON 响应（状态 {response.status_code}）：{resp_text}")
            if raw is None:
                resp = html_response or last_response
                status_code = getattr(resp, "status_code", 200)
                resp_text = (getattr(resp, "text", "") or "")[:500]
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"上游视频接口返回了网页 HTML，而不是 JSON（状态 {status_code}）。\n\n"
                        f"这通常表示 API 设置里的 Base URL 指到了第三方聚合平台的管理后台/网页入口，"
                        f"或该平台不支持当前视频接口路径。请确认 Base URL 是接口地址，例如以 /v1 结尾的 OpenAI 兼容地址，"
                        f"并确认该平台实际支持视频生成端点。\n\n原始响应：{resp_text}"
                    )
                ) from last_json_error
            task_id = extract_task_id(raw) or raw.get("task_id") or raw.get("id")
            result = raw
            if task_id and not video_output_urls(raw):
                result = await wait_for_video_task(client, provider, task_id, submit_url)
            urls = video_output_urls(result)
            if not urls:
                raise HTTPException(status_code=502, detail=f"视频生成成功但没有返回视频：{result}")
            local_urls = [await save_remote_video_to_output(url) for url in urls]
            return {"videos": local_urls, "task_id": task_id, "raw": result}
    except httpx.HTTPStatusError as exc:
        text = exc.response.text
        try:
            requested_model = body.get("model", "") or payload.model or ""
        except NameError:
            requested_model = payload.model or ""
        provider_name = provider.get('name') or provider['id']
        # 1) 模型名不在上游支持范围 → 从错误信息里抽取合法列表展示
        valid_models_match = re.search(r"not in\s*\[([^\]]+)\]", text)
        if valid_models_match:
            valid_models = [m.strip() for m in valid_models_match.group(1).split(",") if m.strip()]
            sample = valid_models[:30]
            more = f"（共 {len(valid_models)} 个，仅显示前 {len(sample)} 个）" if len(valid_models) > len(sample) else ""
            hint = (
                f"上游「{provider_name}」不识别模型「{requested_model}」。\n\n"
                f"上游支持的视频模型清单{more}：\n  {', '.join(sample)}\n\n"
                f"请到「API 设置」里把视频模型改成上面列表中的一个。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        # 2) 模型名合法但账号没开通通道
        if "channel not found" in text or "model_not_found" in text:
            hint = (
                f"上游「{provider_name}」识别了模型「{requested_model}」，但你的 API Key 账号下**没有该模型的可用通道**。\n\n"
                f"原因：你的账号没开通这个模型的访问权限（付费/订阅相关）。\n\n"
                f"解决方法：\n"
                f"  1. 登录 {provider.get('base_url') or '上游平台'} 控制台，开通该模型 / 充值；\n"
                f"  2. 或在「API 设置」里把视频模型改成你账号已开通的型号（如 veo3-fast / veo2-fast / sora-2 等）。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        if "text.duration" in text or "specified duration is not supported" in text:
            hint = (
                f"上游「{provider_name}」模型「{requested_model}」不支持当前时长参数。\n\n"
                f"不同视频模型支持的时长不一样；如果选择了模型不支持的时长，上游可能报错，"
                f"也可能自动按平台默认时长生成，例如 5 秒。\n\n"
                f"请把视频时长切回该模型支持的值，或改用支持更长时长的视频模型。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        if "audio duration" in text.lower():
            too_long = "less than or equal" in text.lower() or "15.2" in text
            bound_hint = "太长（超过 15.2 秒）" if too_long else "太短（不足 1.8 秒）"
            hint = (
                f"上游「{provider_name}」模型「{requested_model}」拒绝了参考音频：时长{bound_hint}。\n\n"
                f"方舟 Seedance 的参考音频时长必须在 1.8 ~ 15.2 秒之间，"
                f"请把音频裁剪到这个区间后再作为参考音频输入。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        if "inputimagesensitivecontentdetected" in text.lower() or "privacyinformation" in text.lower() or "may contain real person" in text.lower():
            hint = (
                f"上游「{provider_name}」拦截了输入参考图，原因是图片里可能包含真人身份/隐私信息。\n\n"
                f"这不是代码协议错误，而是火山视频模型的内容安全策略。\n\n"
                f"建议你这样处理：\n"
                f"  1. 改用非真人参考图，例如插画、AI 头像、商品图、场景图；\n"
                f"  2. 先把真人脸做模糊、遮挡、裁掉，或转成明显的二次元/插画风；\n"
                f"  3. 如果只是想做文生视频，先去掉参考图只保留文字提示词测试。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        raise HTTPException(status_code=exc.response.status_code, detail=f"上游视频接口错误：{text}") from exc
    except httpx.HTTPError as exc:
        # log_net_error(f"视频 网络/TLS错误 provider={provider.get('id')} model={payload.model}", exc)
        raise HTTPException(status_code=502, detail=f"请求上游视频接口失败：{exc}") from exc
