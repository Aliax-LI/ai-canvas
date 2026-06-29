"""ModelScope cloud image generation (angle + ms/generate) — true poll — legacy parity."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.core.media import output_path_for, output_url_for
from infinite_canvas.core.websocket import GLOBAL_LOOP, manager
from infinite_canvas.schemas.canvas_ai import CloudGenRequest, CloudPollRequest, MsGenerateRequest
from infinite_canvas.services import asset_ai, history as history_service
from infinite_canvas.services.modelscope_helpers import (
    modelscope_auth_headers,
    modelscope_image_api_root,
    modelscope_image_url,
    modelscope_size,
    resolve_modelscope_token,
)

TERMINAL_FAILED_STATUSES = {"FAILED", "FAIL", "ERROR", "CANCELED", "CANCELLED", "TIMEOUT", "REVOKED"}


async def _download_modelscope_image(img_url: str, filename_prefix: str) -> str:
    local_path = ""
    try:
        async with httpx.AsyncClient() as dl_client:
            img_res = await dl_client.get(img_url)
            if img_res.status_code == 200:
                filename = f"{filename_prefix}_{int(time.time())}.png"
                file_path = output_path_for(filename, "output")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(img_res.content)
                local_path = output_url_for(filename, "output")
            else:
                local_path = img_url
    except Exception:
        local_path = img_url
    return local_path


async def _poll_modelscope_task(
    client: httpx.AsyncClient,
    task_id: str,
    headers: dict[str, str],
    *,
    max_rounds: int = 300,
    interval: float = 2.0,
    client_id: str | None = None,
    history_type: str = "angle",
    prompt: str = "",
    model: str = "",
) -> dict[str, Any]:
    api_root = modelscope_image_api_root()
    poll_headers = {**headers, "X-ModelScope-Task-Type": "image_generation"}

    for i in range(max_rounds):
        await asyncio.sleep(interval)
        result = await client.get(f"{api_root}/tasks/{task_id}", headers=poll_headers)
        result.raise_for_status()
        data = result.json()
        status = str(data.get("task_status") or "").upper()

        if status == "SUCCEED":
            img_url = data["output_images"][0]
            prefix = "ms" if history_type == "klein" else "cloud_angle"
            if model:
                prefix = f"ms_{model.replace('/', '_').replace(':', '_')}"
            local_path = await _download_modelscope_image(img_url, prefix)
            record: dict[str, Any] = {
                "timestamp": time.time(),
                "prompt": prompt or f"Resumed {task_id}",
                "images": [local_path],
                "type": history_type,
            }
            if model:
                record["model"] = model
            history_service.save_to_history(record)
            if client_id:
                await manager.send_personal_message(
                    {"type": "cloud_status", "status": "SUCCEED", "task_id": task_id},
                    client_id,
                )
            if GLOBAL_LOOP and history_type != "angle":
                asyncio.run_coroutine_threadsafe(manager.broadcast_new_image(record), GLOBAL_LOOP)
            return {"url": local_path, "task_id": task_id}

        if status in TERMINAL_FAILED_STATUSES:
            if client_id:
                await manager.send_personal_message(
                    {"type": "cloud_status", "status": "FAILED", "task_id": task_id},
                    client_id,
                )
            raise HTTPException(status_code=502, detail=f"ModelScope task failed: {data}")

        if i % 5 == 0 and client_id:
            await manager.send_personal_message(
                {
                    "type": "cloud_status",
                    "status": f"{status} ({i}/{max_rounds})",
                    "task_id": task_id,
                    "progress": i,
                    "total": max_rounds,
                },
                client_id,
            )

    if client_id:
        await manager.send_personal_message(
            {"type": "cloud_status", "status": "TIMEOUT", "task_id": task_id},
            client_id,
        )
    return {"status": "timeout", "task_id": task_id, "message": "Task still pending"}


async def poll_angle_status(req: CloudPollRequest) -> dict[str, Any]:
    resolve_modelscope_token(req.api_key)
    headers = modelscope_auth_headers(req.api_key)
    api_root = modelscope_image_api_root()
    task_id = req.task_id

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for i in range(300):
                await asyncio.sleep(2)
                result = await client.get(
                    f"{api_root}/tasks/{task_id}",
                    headers={**headers, "X-ModelScope-Task-Type": "image_generation"},
                )
                result.raise_for_status()
                data = result.json()
                status = str(data.get("task_status") or "").upper()

                if status == "SUCCEED":
                    img_url = data["output_images"][0]
                    local_path = await _download_modelscope_image(img_url, "cloud_angle")
                    record = {
                        "timestamp": time.time(),
                        "prompt": f"Resumed {task_id}",
                        "images": [local_path],
                        "type": "angle",
                    }
                    history_service.save_to_history(record)
                    if req.client_id:
                        await manager.send_personal_message(
                            {"type": "cloud_status", "status": "SUCCEED", "task_id": task_id},
                            req.client_id,
                        )
                    return {"url": local_path}

                if status in TERMINAL_FAILED_STATUSES:
                    if req.client_id:
                        await manager.send_personal_message(
                            {"type": "cloud_status", "status": "FAILED", "task_id": task_id},
                            req.client_id,
                        )
                    raise HTTPException(status_code=502, detail=f"ModelScope task failed: {data}")

                if i % 5 == 0 and req.client_id:
                    await manager.send_personal_message(
                        {
                            "type": "cloud_status",
                            "status": f"{status} ({i}/300)",
                            "task_id": task_id,
                            "progress": i,
                            "total": 300,
                        },
                        req.client_id,
                    )

            if req.client_id:
                await manager.send_personal_message(
                    {"type": "cloud_status", "status": "TIMEOUT", "task_id": task_id},
                    req.client_id,
                )
            return {"status": "timeout", "task_id": task_id, "message": "Task still pending"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def generate_angle(req: CloudGenRequest) -> dict[str, Any]:
    headers = modelscope_auth_headers(req.api_key)
    api_root = modelscope_image_api_root()
    model = asset_ai.selected_model(req.model, "Qwen/Qwen-Image-Edit-2511")
    body: dict[str, Any] = {
        "model": model,
        "prompt": req.prompt.strip(),
        "image_url": [modelscope_image_url(url, max_size=1536) for url in req.image_urls],
    }
    if req.resolution:
        body["size"] = modelscope_size(req.resolution)
    if req.loras is not None:
        body["loras"] = req.loras

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            submit_res = await client.post(f"{api_root}/images/generations", headers=headers, json=body)
            if submit_res.status_code != 200:
                try:
                    detail = submit_res.json()
                except Exception:
                    detail = submit_res.text
                raise HTTPException(status_code=submit_res.status_code, detail=detail)
            task_id = submit_res.json().get("task_id")
            return await _poll_modelscope_task(
                client,
                task_id,
                headers,
                client_id=req.client_id,
                history_type="angle",
                prompt=req.prompt,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def generate_cloud_zimage(req: CloudGenRequest) -> dict[str, Any]:
    """Legacy POST /generate — ModelScope Z-Image Turbo cloud generation."""
    headers = {
        **modelscope_auth_headers(req.api_key, async_mode=True),
    }
    api_root = modelscope_image_api_root()
    body: dict[str, Any] = {
        "model": "Tongyi-MAI/Z-Image-Turbo",
        "prompt": req.prompt.strip(),
        "size": modelscope_size(req.resolution),
        "n": 1,
    }
    if req.loras is not None:
        body["loras"] = req.loras

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            submit_res = await client.post(f"{api_root}/images/generations", headers=headers, json=body)
            if submit_res.status_code != 200:
                try:
                    detail = submit_res.json()
                except Exception:
                    detail = submit_res.text
                raise HTTPException(status_code=submit_res.status_code, detail=detail)
            task_id = submit_res.json().get("task_id")
            return await _poll_modelscope_task(
                client,
                task_id,
                headers,
                max_rounds=200,
                interval=3.0,
                history_type="cloud",
                prompt=req.prompt,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def ms_generate(req: MsGenerateRequest) -> dict[str, Any]:
    headers = modelscope_auth_headers(req.api_key)
    api_root = modelscope_image_api_root()
    body: dict[str, Any] = {
        "model": req.model,
        "prompt": req.prompt.strip(),
    }
    if req.width and req.height:
        body["width"] = req.width
        body["height"] = req.height
        body["size"] = modelscope_size(req.size or f"{req.width}x{req.height}")
    elif req.size:
        body["size"] = modelscope_size(req.size)
    if req.image_urls:
        body["image_url"] = [modelscope_image_url(url, max_size=1536) for url in req.image_urls]
    if req.loras is not None:
        body["loras"] = req.loras

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            submit_res = await client.post(f"{api_root}/images/generations", headers=headers, json=body)
            if submit_res.status_code != 200:
                try:
                    detail = submit_res.json()
                except Exception:
                    detail = submit_res.text
                raise HTTPException(status_code=submit_res.status_code, detail=detail)
            task_id = submit_res.json().get("task_id")
            return await _poll_modelscope_task(
                client,
                task_id,
                headers,
                client_id=req.client_id,
                history_type="klein",
                prompt=req.prompt,
                model=req.model,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
