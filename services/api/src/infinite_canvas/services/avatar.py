"""Asset library avatar registration — legacy parity."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.core.provider_constants import VOLCENGINE_DEFAULT_PROJECT_NAME
from infinite_canvas.core.websocket import now_ms
from infinite_canvas.schemas.asset_libraries import AssetAvatarRegisterRequest
from infinite_canvas.services import asset_ai, asset_library_store, provider_store
from infinite_canvas.services.apimart_media import (
    extract_apimart_avatar_asset_uri,
    upload_media_for_apimart,
    valid_apimart_video_image_input,
)
from infinite_canvas.services.provider_helpers import VIDEO_POLL_TIMEOUT, video_api_root
from infinite_canvas.services.volcengine_assets import (
    check_volcengine_avatar_task,
    submit_volcengine_avatar_asset,
    volcengine_public_asset_url,
)

AVATAR_SUPPORTED_PLATFORMS = {"apimart", "volcengine"}  # 已接入官方资产 API 的平台


AVATAR_TASK_DONE_STATUSES = {"completed", "complete", "succeeded", "success", "active", "done"}


AVATAR_TASK_FAIL_STATUSES = {"failed", "fail", "error", "rejected", "canceled", "cancelled", "expired"}


def avatar_platform_for_provider(provider) -> str:
    if not provider:
        return ""
    if asset_ai.is_apimart_provider(provider):
        return "apimart"
    if asset_ai.is_volcengine_provider(provider):
        return "volcengine"
    return ""


def provider_supports_avatar(provider) -> bool:
    return avatar_platform_for_provider(provider) in AVATAR_SUPPORTED_PLATFORMS


async def submit_apimart_avatar_asset(provider, public_url: str, name: str, kind: str, project_name: str = "default", group_name: str = "") -> str:
    """把一个公网可访问的素材提交到 APIMart private-avatar 审核，立即返回任务 ID（不阻塞轮询）。"""
    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    register_url = f"{base_url}/v1/seedance2/private-avatar"
    body = {
        "project_name": str(project_name or "default").strip() or "default",
        "asset_type": apimart_avatar_asset_type(kind),
        "group": {"name": (group_name or name or "数字人素材")[:60]},
        "assets": [{"url": public_url, "name": (name or "asset")[:60]}],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(register_url, headers=asset_ai.api_headers(provider=provider), json=body, timeout=120)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"APIMart 数字人注册失败（{resp.status_code}）：{resp.text[:300]}")
        data = resp.json()
        task = data.get("data") if isinstance(data.get("data"), dict) else data
        task_id = str(task.get("id") or task.get("task_id") or "").strip()
        if not task_id:
            raise HTTPException(status_code=502, detail=f"APIMart 数字人注册返回中未找到任务 ID：{str(data)[:300]}")
        return task_id


async def check_apimart_avatar_task(provider, task_id: str) -> dict[str, Any]:
    """查询一次 APIMart 审核任务。返回 {status: Active/Processing/Failed, asset_uri, detail}。"""
    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    task_url = f"{base_url}/v1/tasks/{task_id}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(task_url, headers=asset_ai.api_headers(provider=provider), timeout=60)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"查询审核状态失败（{resp.status_code}）：{resp.text[:200]}")
        payload = resp.json()
    node = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    status = str(node.get("status") or "").strip().lower()
    if status in AVATAR_TASK_DONE_STATUSES:
        asset_uri = extract_apimart_avatar_asset_uri(payload)
        if not asset_uri:
            return {"status": "Failed", "asset_uri": "", "detail": "审核完成，但未返回可用的 asset:// 地址（可能部分素材被拒）。"}
        return {"status": "Active", "asset_uri": asset_uri, "detail": ""}
    if status in AVATAR_TASK_FAIL_STATUSES:
        return {"status": "Failed", "asset_uri": "", "detail": f"审核未通过（{status}）。"}
    return {"status": "Processing", "asset_uri": "", "detail": "审核中"}


async def register_asset_library_avatar(item_id: str, payload: AssetAvatarRegisterRequest) -> dict[str, Any]:
    lib = asset_library_store.load_asset_library()
    target_item = asset_library_store.find_asset_item_in_library(lib, item_id, payload.library_id)
    if not target_item:
        raise HTTPException(status_code=404, detail="资产不存在")
    provider = provider_store.get_api_provider(payload.provider_id)
    platform = avatar_platform_for_provider(provider)
    if platform not in AVATAR_SUPPORTED_PLATFORMS:
        name = (provider or {}).get("name") or (provider or {}).get("id") or "该平台"
        raise HTTPException(
            status_code=400,
            detail=f"「{name}」暂不支持数字人/真人认证（目前仅 APIMart 可用，火山等平台待接入官方资产 API）。",
        )
    kind = str(target_item.get("kind") or "image").lower()
    if kind not in ("image", "video", "audio"):
        kind = "image"
    if platform == "apimart":
        project_name = str(payload.project_name or "default").strip() or "default"
        async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as client:
            public_url = await upload_media_for_apimart(client, provider, target_item.get("url") or "", kind)
        if not valid_apimart_video_image_input(public_url):
            reason = public_url[4:] if isinstance(public_url, str) and public_url.startswith("ERR:") else "无法获取公网可访问地址"
            raise HTTPException(
                status_code=400,
                detail=f"素材无法提交到 APIMart：{reason}\n请配置 PUBLIC_BASE_URL，或确认本地文件存在。",
            )
        task_id = await submit_apimart_avatar_asset(
            provider, public_url, target_item.get("name") or "asset", kind,
            project_name=project_name, group_name=payload.group_name,
        )
    elif platform == "volcengine":
        project_name = (
            str(provider.get("volcengine_project_name") or VOLCENGINE_DEFAULT_PROJECT_NAME).strip()
            or VOLCENGINE_DEFAULT_PROJECT_NAME
        )
        public_url = volcengine_public_asset_url(target_item.get("url") or "")
        if public_url.startswith("ERR:"):
            raise HTTPException(status_code=400, detail=public_url[4:])
        task_id = await submit_volcengine_avatar_asset(
            public_url, target_item.get("name") or "asset", kind,
            project_name=project_name, group_name=payload.group_name or "",
        )
    else:
        raise HTTPException(status_code=400, detail="该平台的认证后端尚未接入。")
    regs = target_item.get("registrations")
    if not isinstance(regs, dict):
        regs = {}
    regs[platform] = {
        "provider_id": provider["id"],
        "project_name": project_name,
        "task_id": task_id,
        "status": "Processing",
        "detail": "已提交，审核中",
        "asset_uri": "",
        "asset_id": "",
        "registered_at": now_ms(),
    }
    target_item["registrations"] = regs
    asset_library_store.save_asset_library(lib)
    return {"library": lib, "item": target_item}


async def check_asset_library_avatar(item_id: str, payload: AssetAvatarRegisterRequest) -> dict[str, Any]:
    lib = asset_library_store.load_asset_library()
    target_item = asset_library_store.find_asset_item_in_library(lib, item_id, payload.library_id)
    if not target_item:
        raise HTTPException(status_code=404, detail="资产不存在")
    regs = target_item.get("registrations") if isinstance(target_item.get("registrations"), dict) else {}
    provider = provider_store.get_api_provider(payload.provider_id or "")
    platform = avatar_platform_for_provider(provider)
    if platform not in AVATAR_SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="该平台暂不支持数字人/真人认证审核。")
    reg = regs.get(platform) if isinstance(regs.get(platform), dict) else {}
    task_id = str(reg.get("task_id") or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="该素材还没有提交到这个平台的认证审核。")
    if platform == "apimart":
        result = await check_apimart_avatar_task(provider, task_id)
    elif platform == "volcengine":
        result = await check_volcengine_avatar_task(
            task_id,
            str(reg.get("project_name") or VOLCENGINE_DEFAULT_PROJECT_NAME).strip() or VOLCENGINE_DEFAULT_PROJECT_NAME,
        )
    else:
        raise HTTPException(status_code=400, detail="该平台的认证后端尚未接入。")
    reg["status"] = result["status"]
    reg["detail"] = result.get("detail") or ""
    if result["status"] == "Active" and result.get("asset_uri"):
        reg["asset_uri"] = result["asset_uri"]
        reg["asset_id"] = result["asset_uri"].replace("asset://", "")
    regs[platform] = reg
    target_item["registrations"] = regs
    asset_library_store.save_asset_library(lib)
    return {"library": lib, "item": target_item}
