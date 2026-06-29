"""Smart canvas group export — legacy parity."""

from __future__ import annotations

import os
import shutil
import time

from fastapi import HTTPException

from infinite_canvas.core.media import sanitize_export_filename
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.paths import assets_output_dir, legacy_output_dir
from infinite_canvas.schemas.smart_canvas import SmartCanvasGroupExportRequest


def smart_group_export_folder(folder: str, group_name: str) -> str:
    text = str(folder or "").strip()
    if text:
        path = os.path.abspath(os.path.expanduser(text))
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_group = sanitize_export_filename(group_name or "group", "group")
        output_root = assets_output_dir().parent / "output"
        if legacy_output_dir().is_dir():
            output_root = legacy_output_dir()
        path = os.path.abspath(output_root / "smart-groups" / f"{safe_group}-{stamp}")
    os.makedirs(path, exist_ok=True)
    return path


async def export_smart_canvas_group(payload: SmartCanvasGroupExportRequest) -> dict[str, object]:
    target_dir = smart_group_export_folder(payload.folder, payload.group_name)
    used_names: set[str] = set()
    count = 0
    text_index = 1
    for item in payload.items[:2000]:
        kind = str(item.kind or "").lower()
        if kind == "text":
            text = str(item.text or "")
            if not text.strip():
                continue
            base = sanitize_export_filename(item.name or f"{text_index}.txt", f"{text_index}.txt")
            if not base.lower().endswith(".txt"):
                base += ".txt"
            text_index += 1
            name, ext = os.path.splitext(base)
            out_name = base
            suffix = 2
            while out_name in used_names:
                out_name = f"{name}-{suffix}{ext}"
                suffix += 1
            used_names.add(out_name)
            with open(os.path.join(target_dir, out_name), "w", encoding="utf-8") as f:
                f.write(text)
            count += 1
            continue
        src_path = output_file_from_url(item.url)
        src = str(src_path) if src_path else ""
        if not src or not os.path.isfile(src):
            continue
        base = sanitize_export_filename(item.name or os.path.basename(src), os.path.basename(src) or f"asset-{count + 1}")
        name, ext = os.path.splitext(base)
        if not ext:
            _, src_ext = os.path.splitext(src)
            ext = src_ext or ".bin"
            base = name + ext
        out_name = base
        suffix = 2
        while out_name in used_names:
            out_name = f"{name}-{suffix}{ext}"
            suffix += 1
        used_names.add(out_name)
        shutil.copy2(src, os.path.join(target_dir, out_name))
        count += 1
    if count <= 0:
        raise HTTPException(status_code=404, detail="没有可导出的内容")
    return {"ok": True, "folder": target_dir, "count": count}
