"""GitHub / ModelScope app update — legacy parity."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from threading import Lock, Thread
from typing import Any

import requests
from fastapi import HTTPException

from infinite_canvas import __version__
from infinite_canvas.core.paths import app_data_dir, coding_root, legacy_static_dir, repo_root
from infinite_canvas.schemas.update import RollbackRequest, UpdateRequest

GITHUB_REPO_URL = "https://github.com/hero8152/Infinite-Canvas"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/hero8152/Infinite-Canvas/main/VERSION"
GITHUB_TREE_URL = "https://api.github.com/repos/hero8152/Infinite-Canvas/git/trees/main?recursive=1"
GITHUB_RAW_ROOT = "https://raw.githubusercontent.com/hero8152/Infinite-Canvas/main"
GITHUB_UPDATE_NOTES_URL = GITHUB_RAW_ROOT + "/static/update-notes.json"
MODELSCOPE_REPO_URL = "https://modelscope.ai/studios/daniel8152/Infinite-Canvas"
MODELSCOPE_FILE_API_ROOT = (
    "https://www.modelscope.ai/api/v1/studio/daniel8152/Infinite-Canvas/repo?Revision=master&FilePath="
)
MODELSCOPE_VERSION_URL = MODELSCOPE_FILE_API_ROOT + "VERSION"
MODELSCOPE_UPDATE_NOTES_URL = MODELSCOPE_FILE_API_ROOT + "static/update-notes.json"
MODELSCOPE_TREE_URL = (
    "https://www.modelscope.ai/api/v1/studio/daniel8152/Infinite-Canvas/repo/files?Revision=master&Recursive=true"
)

UPDATE_LOCK = Lock()
GITHUB_TREE_CACHE: dict[str, Any] = {"etag": "", "data": None, "expires_at": 0.0}
UPDATE_SOURCE_LABELS = {"github": "GitHub", "modelscope": "ModelScope"}


def update_base_dir() -> str:
    coding = coding_root()
    if coding.is_dir():
        return str(coding)
    return str(repo_root())


def update_backups_root() -> str:
    return str(app_data_dir() / "data" / "update_backups")


def current_app_version() -> str:
    version_file = repo_root() / "VERSION"
    try:
        if version_file.is_file():
            version = (version_file.read_text(encoding="utf-8").strip().splitlines() or [""])[0].strip()
            if version:
                return version
    except Exception:
        pass
    coding_version = coding_root() / "VERSION"
    try:
        if coding_version.is_file():
            version = (coding_version.read_text(encoding="utf-8").strip().splitlines() or [""])[0].strip()
            if version:
                return version
    except Exception:
        pass
    return __version__


def update_notes_path() -> str:
    static = legacy_static_dir()
    if static.is_dir():
        return str(static / "update-notes.json")
    return str(repo_root() / "static" / "update-notes.json")


def safe_update_notes(payload: Any, version: str = "") -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    items = payload.get("items")
    if not isinstance(items, list):
        items = []
    clean_items = []
    for item in items[:30]:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("title") or "").strip()
            if not text:
                continue
            clean_items.append({"type": str(item.get("type") or "update").strip()[:32], "text": text[:500]})
        else:
            text = str(item or "").strip()
            if text:
                clean_items.append({"type": "update", "text": text[:500]})
    notes_version = str(payload.get("version") or version or "").strip()
    history = payload.get("history")
    selected_history: dict[str, Any] = {}
    if version and isinstance(history, list):
        for entry in history:
            if isinstance(entry, dict) and str(entry.get("version") or "").strip() == version:
                selected_history = safe_update_notes(entry, version)
                break
    if selected_history:
        return selected_history
    return {
        "version": notes_version,
        "updated_at": str(payload.get("updated_at") or payload.get("date") or "").strip(),
        "items": clean_items,
    }


def read_local_update_notes(version: str = "") -> dict[str, Any]:
    try:
        path = update_notes_path()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return safe_update_notes(json.load(f), version)
    except Exception:
        pass
    return {"version": version or current_app_version(), "updated_at": "", "items": []}


def connectivity_probe(name: str, url: str, timeout: float = 5.0) -> dict[str, Any]:
    started = time.time()
    item: dict[str, Any] = {
        "name": name,
        "url": url,
        "ok": False,
        "status": 0,
        "elapsed_ms": 0,
        "error": "",
        "timed_out": False,
    }
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Infinite-Canvas-Updater"},
            timeout=timeout,
            stream=True,
            proxies=urllib.request.getproxies() or None,
        )
        item["status"] = response.status_code
        item["ok"] = 200 <= response.status_code < 400
        if not item["ok"]:
            item["error"] = f"HTTP {response.status_code} {response.reason}"
        response.close()
    except requests.Timeout:
        item["timed_out"] = True
        item["error"] = f"连接超时（超过 {timeout:g}s）"
    except requests.RequestException as exc:
        item["error"] = str(exc)
    finally:
        item["elapsed_ms"] = int((time.time() - started) * 1000)
    return item


def update_connectivity_targets() -> list[tuple[str, str, str, bool]]:
    return [
        ("GitHub 更新列表", GITHUB_TREE_URL, "github", True),
        ("GitHub 版本文件", GITHUB_VERSION_URL, "github", True),
        ("GitHub 主页", "https://github.com/", "github", False),
        ("ModelScope 版本文件", MODELSCOPE_VERSION_URL, "modelscope", True),
        ("ModelScope 空间页面", MODELSCOPE_REPO_URL, "modelscope", False),
        ("ModelScope 主页", "https://modelscope.cn/", "modelscope", False),
        ("Google 连通性", "https://www.google.com/generate_204", "reference", False),
    ]


def update_connectivity_probe(name: str) -> dict[str, Any]:
    for t_name, url, source, required in update_connectivity_targets():
        if t_name == name:
            item = connectivity_probe(t_name, url)
            item["source"] = source
            item["required"] = required
            return item
    raise HTTPException(status_code=404, detail="未知的连通性检测目标")


def update_connectivity() -> dict[str, Any]:
    targets = update_connectivity_targets()
    results = []
    for t_name, url, source, required in targets:
        item = connectivity_probe(t_name, url)
        item["source"] = source
        item["required"] = required
        results.append(item)
    sources: dict[str, Any] = {}
    for source in ("github", "modelscope"):
        source_required = [item for item in results if item.get("source") == source and item.get("required")]
        sources[source] = {
            "ok": all(item["ok"] for item in source_required),
            "required": [item["name"] for item in source_required],
        }
    return {
        "ok": sources["github"]["ok"],
        "results": results,
        "sources": sources,
        "required": sources["github"]["required"],
        "optional": ["GitHub 主页", "ModelScope 空间页面", "ModelScope 主页", "Google 连通性"],
    }


def fetch_remote_version(url: str, timeout: float = 5.0) -> dict[str, Any]:
    info: dict[str, Any] = {"version": "", "ok": False, "error": "", "url": url}
    if not url:
        info["error"] = "missing url"
        return info
    try:
        resp = requests.get(
            f"{url}{'&' if '?' in url else '?'}t={int(time.time())}",
            headers={"User-Agent": "Infinite-Canvas-Updater"},
            timeout=timeout,
            proxies=urllib.request.getproxies() or None,
        )
        if 200 <= resp.status_code < 400:
            text = resp.content.decode("utf-8", errors="replace").strip()
            version = text.splitlines()[0].strip() if text else ""
            if version and "<" not in version and "{" not in version and re.search(r"\d", version):
                info["version"] = version
                info["ok"] = True
            elif not version:
                info["error"] = "空版本文件"
            else:
                info["error"] = "版本文件格式异常"
        else:
            info["error"] = f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        info["error"] = str(exc)
    return info


def version_tuple(value: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(value or ""))]


def version_gt(a: str, b: str) -> bool:
    ta, tb = version_tuple(a), version_tuple(b)
    n = max(len(ta), len(tb))
    ta += [0] * (n - len(ta))
    tb += [0] * (n - len(tb))
    return ta > tb


def fetch_remote_update_notes(url: str, version: str = "", timeout: float = 5.0) -> dict[str, Any]:
    info: dict[str, Any] = {"ok": False, "error": "", "url": url, "version": version, "items": []}
    if not url:
        info["error"] = "missing url"
        return info
    try:
        resp = requests.get(
            f"{url}{'&' if '?' in url else '?'}t={int(time.time())}",
            headers={"User-Agent": "Infinite-Canvas-Updater"},
            timeout=timeout,
            proxies=urllib.request.getproxies() or None,
        )
        if 200 <= resp.status_code < 400:
            payload = json.loads(resp.content.decode("utf-8", errors="replace"))
            notes = safe_update_notes(payload, version)
            info.update(notes)
            info["ok"] = True
        else:
            info["error"] = f"HTTP {resp.status_code}"
    except Exception as exc:
        info["error"] = str(exc)
    return info


def fetch_update_notes_with_fallback(
    preferred_source: str, version: str, timeout: float = 3.0
) -> tuple[dict[str, Any], dict[str, Any]]:
    urls = {"github": GITHUB_UPDATE_NOTES_URL, "modelscope": MODELSCOPE_UPDATE_NOTES_URL}
    preferred = preferred_source if preferred_source in urls else "github"
    order = [preferred, "modelscope" if preferred == "github" else "github"]
    notes_by_source: dict[str, Any] = {}
    best_notes: dict[str, Any] = {"version": version, "items": []}
    for source in order:
        notes = fetch_remote_update_notes(urls[source], version, timeout=timeout)
        notes["source"] = source
        notes_by_source[source] = notes
        if notes.get("ok") and (notes.get("items") or []):
            best_notes = notes
            break
    for source, url in urls.items():
        if source not in notes_by_source:
            notes_by_source[source] = {
                "ok": False,
                "error": "未尝试：已有更新说明可用" if best_notes.get("items") else "未尝试",
                "url": url,
                "source": source,
                "version": version,
                "items": [],
            }
    return best_notes, notes_by_source


def check_update() -> dict[str, Any]:
    current = current_app_version()
    holder: dict[str, dict[str, Any]] = {}

    def _probe(key: str, url: str) -> None:
        item = fetch_remote_version(url, timeout=5.0)
        item["source"] = key
        holder[key] = item

    threads = [
        Thread(target=_probe, args=("github", GITHUB_VERSION_URL), daemon=True),
        Thread(target=_probe, args=("modelscope", MODELSCOPE_VERSION_URL), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5.5)
    github = holder.get("github") or {
        "version": "",
        "ok": False,
        "error": "检测超时（超过 5s）",
        "url": GITHUB_VERSION_URL,
        "source": "github",
    }
    modelscope = holder.get("modelscope") or {
        "version": "",
        "ok": False,
        "error": "检测超时（超过 5s）",
        "url": MODELSCOPE_VERSION_URL,
        "source": "modelscope",
    }
    best: dict[str, Any] = {}
    for item in (github, modelscope):
        if item["ok"] and item["version"]:
            if not best or version_gt(item["version"], best["version"]):
                best = {"source": item["source"], "version": item["version"]}
    update_available = bool(best and version_gt(best["version"], current))
    notes_by_source: dict[str, Any] = {}
    if best and best.get("version"):
        best_notes, notes_by_source = fetch_update_notes_with_fallback(
            str(best.get("source") or "github"), best["version"], timeout=3.0
        )
        best["update_notes"] = best_notes if best_notes.get("ok") else {"version": best["version"], "items": []}
    return {
        "current": current,
        "github": github,
        "modelscope": modelscope,
        "latest": best,
        "update_notes": best.get("update_notes") if best else {},
        "update_notes_sources": notes_by_source,
        "update_available": update_available,
        "reachable": bool(github["ok"] or modelscope["ok"]),
    }


def update_allowed_file(path: str) -> bool:
    path = str(path or "").replace("\\", "/").lstrip("/")
    if not path or any(part in {"", ".", ".."} for part in path.split("/")):
        return False
    return path in {"main.py", "VERSION"} or path.startswith("static/")


def safe_update_target(path: str) -> str:
    rel = str(path or "").replace("\\", "/").lstrip("/")
    if not update_allowed_file(rel):
        raise ValueError(f"更新文件不在允许范围：{rel}")
    target = os.path.abspath(os.path.join(update_base_dir(), *rel.split("/")))
    base = os.path.abspath(update_base_dir())
    if os.path.commonpath([base, target]) != base:
        raise ValueError(f"更新路径不安全：{rel}")
    return target


def safe_static_dir() -> str:
    static = legacy_static_dir()
    if static.is_dir():
        target = str(static.resolve())
    else:
        target = os.path.abspath(os.path.join(update_base_dir(), "static"))
    base = os.path.abspath(update_base_dir())
    if os.path.commonpath([base, target]) != base:
        raise RuntimeError(f"static 路径不安全：{target}")
    return target


def schedule_self_restart(delay_seconds: int = 3) -> bool:
    return False


def normalize_update_source(value: str) -> str:
    source = str(value or "github").strip().lower()
    if source == "ms":
        return "modelscope"
    if source not in {"github", "modelscope"}:
        return "github"
    return source


def github_get(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> requests.Response:
    try:
        response = requests.get(
            url,
            headers=headers or {},
            timeout=timeout,
            proxies=urllib.request.getproxies() or None,
        )
    except requests.RequestException as exc:
        raise urllib.error.URLError(str(exc)) from exc
    if response.status_code >= 400 or response.status_code == 304:
        raise urllib.error.HTTPError(url, response.status_code, response.reason, response.headers, None)
    return response


def github_json(url: str, use_etag_cache: bool = False) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Infinite-Canvas-Updater",
    }
    cache_key = url
    if use_etag_cache and cache_key == GITHUB_TREE_URL:
        if GITHUB_TREE_CACHE["data"] and time.time() < GITHUB_TREE_CACHE["expires_at"]:
            return GITHUB_TREE_CACHE["data"]
        if GITHUB_TREE_CACHE["etag"]:
            headers["If-None-Match"] = GITHUB_TREE_CACHE["etag"]
    try:
        resp = github_get(url, headers=headers, timeout=30)
        etag = resp.headers.get("ETag", "")
        payload = json.loads(resp.content.decode("utf-8", errors="replace"))
        if use_etag_cache and cache_key == GITHUB_TREE_URL:
            GITHUB_TREE_CACHE.update({"etag": etag, "data": payload, "expires_at": time.time() + 600})
        return payload
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and use_etag_cache and GITHUB_TREE_CACHE["data"]:
            GITHUB_TREE_CACHE["expires_at"] = time.time() + 600
            return GITHUB_TREE_CACHE["data"]
        raise


def github_bytes(url: str) -> bytes:
    resp = github_get(url, headers={"User-Agent": "Infinite-Canvas-Updater"}, timeout=60)
    return resp.content


def download_github_update_files(files: list[str], staging_root: str) -> None:
    staging_root_abs = os.path.abspath(staging_root)
    for rel in files:
        safe_update_target(rel)
        raw_url = f"{GITHUB_RAW_ROOT}/{urllib.parse.quote(rel, safe='/')}"
        data = github_bytes(raw_url)
        stage_path = os.path.abspath(os.path.join(staging_root_abs, *rel.split("/")))
        if os.path.commonpath([staging_root_abs, stage_path]) != staging_root_abs:
            raise ValueError(f"更新暂存路径不安全：{rel}")
        os.makedirs(os.path.dirname(stage_path), exist_ok=True)
        with open(stage_path, "wb") as f:
            f.write(data)


def github_update_file_list() -> tuple[list[str], list[str], list[str]]:
    tree_data = github_json(GITHUB_TREE_URL, use_etag_cache=True)
    entries = tree_data.get("tree") or []
    static_files: list[str] = []
    root_files: list[str] = []
    for entry in entries:
        path = str(entry.get("path") or "").replace("\\", "/")
        if entry.get("type") == "blob" and update_allowed_file(path):
            if path.startswith("static/"):
                static_files.append(path)
            else:
                root_files.append(path)
    if "main.py" not in root_files:
        root_files.append("main.py")
    if "VERSION" not in root_files:
        root_files.append("VERSION")
    static_files = sorted(set(static_files))
    root_files = sorted(set(root_files))
    files = root_files + static_files
    if not static_files:
        raise RuntimeError("GitHub 未返回 static 文件，已取消更新")
    return root_files, static_files, files


def staged_update_file_list(staging_root: str) -> tuple[list[str], list[str], list[str]]:
    root_files: list[str] = []
    static_files: list[str] = []
    for root_dir, _, names in os.walk(staging_root):
        for name in names:
            path = os.path.abspath(os.path.join(root_dir, name))
            rel = os.path.relpath(path, staging_root).replace("\\", "/")
            if not update_allowed_file(rel):
                continue
            if rel.startswith("static/"):
                static_files.append(rel)
            else:
                root_files.append(rel)
    if "main.py" not in root_files or "VERSION" not in root_files:
        raise RuntimeError("更新源缺少 main.py 或 VERSION")
    if not static_files:
        raise RuntimeError("更新源未返回 static 文件，已取消更新")
    root_files = sorted(set(root_files))
    static_files = sorted(set(static_files))
    return root_files, static_files, root_files + static_files


def modelscope_update_file_list() -> list[str]:
    resp = github_get(MODELSCOPE_TREE_URL, headers={"User-Agent": "Infinite-Canvas-Updater"}, timeout=30)
    payload = json.loads(resp.content.decode("utf-8", errors="replace"))
    files_node = ((payload.get("Data") or {}).get("Files")) or []
    out: list[str] = []
    for entry in files_node:
        if not isinstance(entry, dict):
            continue
        if entry.get("Type") != "blob":
            continue
        path = str(entry.get("Path") or "").replace("\\", "/")
        if update_allowed_file(path):
            out.append(path)
    return sorted(set(out))


def modelscope_file_bytes(rel: str) -> bytes:
    url = MODELSCOPE_FILE_API_ROOT + urllib.parse.quote(rel, safe="/")
    resp = github_get(url, headers={"User-Agent": "Infinite-Canvas-Updater"}, timeout=60)
    return resp.content


def download_modelscope_update_files(staging_root: str) -> list[str]:
    files = modelscope_update_file_list()
    if not files:
        raise RuntimeError("ModelScope 未返回任何文件")
    if "main.py" not in files or "VERSION" not in files:
        raise RuntimeError("ModelScope 更新源缺少 main.py 或 VERSION")
    if not any(f.startswith("static/") for f in files):
        raise RuntimeError("ModelScope 未返回 static 文件，已取消更新")
    staging_root_abs = os.path.abspath(staging_root)
    for rel in files:
        safe_update_target(rel)
        data = modelscope_file_bytes(rel)
        stage_path = os.path.abspath(os.path.join(staging_root_abs, *rel.split("/")))
        if os.path.commonpath([staging_root_abs, stage_path]) != staging_root_abs:
            raise ValueError(f"更新暂存路径不安全：{rel}")
        os.makedirs(os.path.dirname(stage_path), exist_ok=True)
        with open(stage_path, "wb") as f:
            f.write(data)
    return files


def stage_update_from_source(source: str, staging_root: str) -> tuple[list[str], list[str], list[str]]:
    if source == "modelscope":
        download_modelscope_update_files(staging_root)
        return staged_update_file_list(staging_root)
    root_files, static_files, files = github_update_file_list()
    download_github_update_files(files, staging_root)
    return root_files, static_files, files


def update_from_github(req: UpdateRequest) -> dict[str, Any]:
    if not UPDATE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="正在更新中，请稍后再试")
    staging_root = ""
    requested_source = normalize_update_source(req.source)
    source_order = [requested_source]
    if req.fallback:
        other = "modelscope" if requested_source == "github" else "github"
        source_order.append(other)
    try:
        backup_root = os.path.join(update_backups_root(), time.strftime("%Y%m%d-%H%M%S"))
        source = requested_source
        root_files = static_files = files = None
        download_errors: list[str] = []
        fallback_used = False
        for idx, candidate in enumerate(source_order):
            attempt_staging = os.path.join(
                app_data_dir() / "data" / "update_staging",
                f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{candidate}",
            )
            attempt_staging = str(attempt_staging)
            if os.path.isdir(attempt_staging):
                shutil.rmtree(attempt_staging, ignore_errors=True)
            label = UPDATE_SOURCE_LABELS.get(candidate, candidate)
            try:
                root_files, static_files, files = stage_update_from_source(candidate, attempt_staging)
                source = candidate
                staging_root = attempt_staging
                fallback_used = idx > 0
                break
            except Exception as exc:
                if os.path.isdir(attempt_staging):
                    shutil.rmtree(attempt_staging, ignore_errors=True)
                download_errors.append(f"{label}：{exc}")
        if not staging_root:
            detail = "；".join(download_errors) or "未知错误"
            raise HTTPException(status_code=502, detail=f"所有下载源均失败 → {detail}")

        updated: list[str] = []
        for rel in root_files or []:
            target = safe_update_target(rel)
            if os.path.exists(target):
                backup_path = os.path.join(backup_root, *rel.split("/"))
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(target, backup_path)

        staged_static_dir = os.path.join(staging_root, "static")
        if not os.path.isdir(staged_static_dir):
            raise RuntimeError("GitHub static 暂存目录不存在，已取消更新")
        static_dir = safe_static_dir()
        backup_static_dir = os.path.join(backup_root, "static")
        if os.path.isdir(static_dir):
            os.makedirs(os.path.dirname(backup_static_dir), exist_ok=True)
            shutil.copytree(static_dir, backup_static_dir)
            shutil.rmtree(static_dir)
        shutil.copytree(staged_static_dir, static_dir)
        updated.extend(static_files or [])

        replaced_root_files: list[str] = []
        try:
            for rel in root_files or []:
                target = safe_update_target(rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                temp_path = f"{target}.update_tmp"
                shutil.copy2(os.path.join(staging_root, *rel.split("/")), temp_path)
                os.replace(temp_path, target)
                replaced_root_files.append(rel)
                updated.append(rel)
        except Exception:
            for rel in reversed(replaced_root_files):
                backup_path = os.path.join(backup_root, *rel.split("/"))
                target = safe_update_target(rel)
                if os.path.exists(backup_path):
                    temp_path = f"{target}.rollback_tmp"
                    shutil.copy2(backup_path, temp_path)
                    os.replace(temp_path, target)
            if os.path.isdir(static_dir):
                shutil.rmtree(static_dir, ignore_errors=True)
            if os.path.isdir(backup_static_dir):
                shutil.copytree(backup_static_dir, static_dir)
            raise

        restart_scheduled = bool(req.auto_restart and updated and schedule_self_restart(req.restart_delay))
        new_version = ""
        try:
            staged_version = os.path.join(staging_root, "VERSION")
            if os.path.exists(staged_version):
                with open(staged_version, encoding="utf-8") as f:
                    new_version = (f.read().strip().splitlines() or [""])[0].strip()
        except Exception:
            new_version = ""
        notes_file = os.path.join(staging_root, "static", "update-notes.json")
        update_notes: dict[str, Any] = {}
        try:
            if os.path.exists(notes_file):
                with open(notes_file, encoding="utf-8") as f:
                    update_notes = safe_update_notes(json.load(f), new_version)
        except Exception:
            update_notes = {}
        return {
            "ok": True,
            "source": source,
            "source_label": UPDATE_SOURCE_LABELS.get(source, source),
            "requested_source": requested_source,
            "fallback_used": fallback_used,
            "download_errors": download_errors,
            "updated": updated,
            "count": len(updated),
            "version": new_version,
            "update_notes": update_notes,
            "backup_dir": backup_root if os.path.exists(backup_root) else "",
            "restart_required": True,
            "restart_scheduled": restart_scheduled,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新失败：{exc}") from exc
    finally:
        if staging_root and os.path.isdir(staging_root):
            shutil.rmtree(staging_root, ignore_errors=True)
        UPDATE_LOCK.release()


def list_update_backups() -> list[dict[str, Any]]:
    root = update_backups_root()
    if not os.path.isdir(root):
        return []
    items: list[dict[str, Any]] = []
    for name in sorted(os.listdir(root), reverse=True):
        bp = os.path.join(root, name)
        if not os.path.isdir(bp):
            continue
        file_count = 0
        for _, _, fs in os.walk(bp):
            file_count += len(fs)
        try:
            created_at = os.path.getmtime(bp)
        except OSError:
            created_at = 0.0
        items.append({"name": name, "file_count": file_count, "created_at": created_at})
    return items


def rollback_update(req: RollbackRequest) -> dict[str, Any]:
    if not req.name:
        raise HTTPException(status_code=400, detail="缺少备份名称")
    if not UPDATE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="正在更新中，请稍后再试")
    try:
        backup_root_abs = os.path.abspath(update_backups_root())
        backup_dir = os.path.abspath(os.path.join(backup_root_abs, req.name))
        if os.path.commonpath([backup_root_abs, backup_dir]) != backup_root_abs:
            raise HTTPException(status_code=400, detail="备份路径不安全")
        if not os.path.isdir(backup_dir):
            raise HTTPException(status_code=404, detail="备份不存在")
        restored: list[str] = []
        skipped: list[str] = []
        backup_static_dir = os.path.join(backup_dir, "static")
        if os.path.isdir(backup_static_dir):
            static_dir = safe_static_dir()
            if os.path.isdir(static_dir):
                shutil.rmtree(static_dir)
            shutil.copytree(backup_static_dir, static_dir)
            for dirpath, _, filenames in os.walk(backup_static_dir):
                for fn in filenames:
                    src = os.path.join(dirpath, fn)
                    restored.append(os.path.relpath(src, backup_dir).replace("\\", "/"))
        for dirpath, _, filenames in os.walk(backup_dir):
            for fn in filenames:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, backup_dir).replace("\\", "/")
                if rel.startswith("static/"):
                    continue
                if not update_allowed_file(rel):
                    skipped.append(rel)
                    continue
                try:
                    target = safe_update_target(rel)
                except ValueError:
                    skipped.append(rel)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                temp_path = f"{target}.rollback_tmp"
                with open(src, "rb") as fin, open(temp_path, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
                os.replace(temp_path, target)
                restored.append(rel)
        restart_scheduled = bool(req.auto_restart and restored and schedule_self_restart(req.restart_delay))
        return {
            "ok": True,
            "restored": restored,
            "skipped": skipped,
            "count": len(restored),
            "restart_required": True,
            "restart_scheduled": restart_scheduled,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"回滚失败：{exc}") from exc
    finally:
        UPDATE_LOCK.release()
