# M10 — 将 Python 后端打包为 Tauri sidecar 二进制
#
# 入口与 pyproject [project.scripts] 一致：infinite_canvas.main:main
#
# 用法（在仓库根目录，PowerShell）：
#   .\scripts\build-sidecar.ps1
#
# 产出：apps/desktop/src-tauri/binaries/infinite-canvas-<target-triple>.exe

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$TargetTriple = (rustc -vV | Select-String "host: (.+)" | ForEach-Object { $_.Matches.Groups[1].Value })
$OutDir = Join-Path $Root "apps/desktop/src-tauri/binaries"
$BinaryName = "infinite-canvas-$TargetTriple.exe"
$PythonPath = Join-Path $Root "services/api/src"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "==> 同步 Python 依赖（含 PyInstaller dev 组）"
uv sync --group dev

Write-Host "==> PyInstaller 打包 infinite-canvas CLI (infinite_canvas.main:main)"
$env:PYTHONPATH = "$PythonPath;$env:PYTHONPATH"
uv run pyinstaller `
  --name infinite-canvas `
  --onefile `
  --clean `
  --console `
  --paths $PythonPath `
  --distpath (Join-Path $OutDir "dist") `
  --workpath (Join-Path $OutDir "build") `
  --specpath $OutDir `
  --hidden-import infinite_canvas `
  --collect-submodules infinite_canvas `
  --collect-submodules uvicorn `
  --collect-submodules fastapi `
  --collect-submodules starlette `
  --collect-submodules pydantic `
  --copy-metadata infinite-canvas `
  (Join-Path $Root "scripts/sidecar_entry.py")

Move-Item -Force (Join-Path $OutDir "dist/infinite-canvas.exe") (Join-Path $OutDir $BinaryName)

Remove-Item -Recurse -Force (Join-Path $OutDir "dist"), (Join-Path $OutDir "build") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $OutDir "infinite-canvas.spec") -ErrorAction SilentlyContinue

$Size = (Get-Item (Join-Path $OutDir $BinaryName)).Length / 1MB
Write-Host "==> 完成: $OutDir\$BinaryName ($([math]::Round($Size, 1)) MB)"
Write-Host "下一步: Authenticode 签名（Windows）"
