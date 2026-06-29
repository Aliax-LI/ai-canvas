import io
import json
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from infinite_canvas.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_canvas_assets_empty(client):
    response = await client.get("/api/canvas-assets")
    assert response.status_code == 200
    body = response.json()
    assert body["categories"]
    assert body["canvases"] == []
    assert body["items"] == []


@pytest.mark.asyncio
async def test_canvas_assets_index_with_canvas(client, data_dir):
    create = await client.post(
        "/api/canvases",
        json={"title": "资产测试", "kind": "smart"},
    )
    canvas_id = create.json()["canvas"]["id"]
    asset_url = "/assets/input/test-asset.png"
    input_dir = data_dir / "assets" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "test-asset.png").write_bytes(_png_bytes())

    get_resp = await client.get(f"/api/canvases/{canvas_id}")
    canvas = get_resp.json()["canvas"]
    save = await client.put(
        f"/api/canvases/{canvas_id}",
        json={
            "title": canvas["title"],
            "nodes": [
                {
                    "id": "n1",
                    "type": "image",
                    "title": "参考图",
                    "url": asset_url,
                }
            ],
            "connections": [],
            "base_updated_at": canvas["updated_at"],
        },
    )
    assert save.status_code == 200

    index = await client.get("/api/canvas-assets")
    assert index.status_code == 200
    body = index.json()
    assert len(body["canvases"]) == 1
    assert body["canvases"][0]["asset_count"] >= 1
    assert any(item["url"] == asset_url for item in body["items"])


@pytest.mark.asyncio
async def test_canvas_assets_check_and_download(client, data_dir):
    input_dir = data_dir / "assets" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "dl.png").write_bytes(_png_bytes())
    url = "/assets/input/dl.png"

    check = await client.post("/api/canvas-assets/check", json={"urls": [url, "https://example.com/x.png"]})
    assert check.status_code == 200
    exists = check.json()["exists"]
    assert exists[url] is True
    assert exists["https://example.com/x.png"] is True

    download = await client.post(
        "/api/canvas-assets/download",
        json={"items": [{"url": url, "name": "exported.png"}]},
    )
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(download.content)) as zf:
        names = zf.namelist()
        assert any(name.endswith(".png") for name in names)


@pytest.mark.asyncio
async def test_prompt_templates(client):
    response = await client.get("/api/smart-canvas/prompt-templates")
    assert response.status_code == 200
    body = response.json()
    assert "templates" in body
    assert isinstance(body["templates"], list)


@pytest.mark.asyncio
async def test_canvas_workflow_export_import(client, data_dir):
    input_dir = data_dir / "assets" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "wf-res.png").write_bytes(_png_bytes())
    nodes = [{"id": "a", "image": "/assets/input/wf-res.png"}]
    export = await client.post(
        "/api/canvas-workflows/export",
        json={"nodes": nodes, "connections": [], "include_resources": True},
    )
    assert export.status_code == 200
    assert export.headers["content-type"] == "application/zip"
    archive = export.content

    files = {"file": ("workflow.zip", archive, "application/zip")}
    imported = await client.post("/api/canvas-workflows/import", files=files)
    assert imported.status_code == 200
    body = imported.json()
    assert body["nodes"]
    assert body["workflow"]["format"] == "infinite-canvas-workflow"


@pytest.mark.asyncio
async def test_export_workflow_to_library(client):
    nodes = [{"id": "node-1", "type": "text", "text": "hello"}]
    response = await client.post(
        "/api/canvas-workflows/export-to-library",
        json={"nodes": nodes, "connections": [], "include_resources": False, "name": "测试工作流"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["item"]["kind"] == "workflow"
    assert body["library"]["libraries"]


@pytest.mark.asyncio
async def test_upload_workflow_to_library(client):
    workflow = {"nodes": [{"id": "n1"}], "connections": []}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("workflow.json", json.dumps(workflow))
    files = {"files": ("wf.zip", buf.getvalue(), "application/zip")}
    response = await client.post("/api/asset-library/workflows/upload", files=files)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["kind"] == "workflow"
