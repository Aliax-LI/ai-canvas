# M10 — 将 Python 后端打包为 Tauri sidecar 二进制（占位脚本，Batch 2+ 完善）
#
# 前置：uv、PyInstaller
#   uv pip install pyinstaller
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

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "==> 同步 Python 依赖"
uv sync

Write-Host "==> PyInstaller 打包 infinite-canvas CLI"
uv run pyinstaller `
  --name infinite-canvas `
  --onefile `
  --clean `
  --distpath (Join-Path $OutDir "dist") `
  --workpath (Join-Path $OutDir "build") `
  --specpath $OutDir `
  --hidden-import infinite_canvas `
  --collect-submodules infinite_canvas `
  services/api/src/infinite_canvas/main.py

Move-Item -Force (Join-Path $OutDir "dist/infinite-canvas.exe") (Join-Path $OutDir $BinaryName)

Write-Host "==> 完成: $OutDir\$BinaryName"
Write-Host "下一步: Authenticode 签名（Windows）"
