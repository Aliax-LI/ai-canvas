# M10 — Tauri 2 桌面端计划与验证清单

> 设计规格 §7 · Batch 2 完成 PyInstaller sidecar + prod 打包链路

## Batch 1 范围（已完成）

- [x] `apps/desktop/` Tauri 2 scaffold
- [x] Rust sidecar：`uv run infinite-canvas`，端口 3000+ 自增，健康检查 60s
- [x] 关窗 / 退出 kill 子进程
- [x] 前端 API base 注入（`__INFINITE_CANVAS_API__` + Tauri invoke fallback）
- [x] 系统托盘：显示/隐藏、退出
- [x] `externalBin` 占位 + `scripts/build-sidecar.*`
- [x] E2E stub + 手动验证文档

## Batch 2 范围（本批）

- [x] `scripts/build-sidecar.sh` / `.ps1`：PyInstaller onefile，入口 `infinite_canvas.main:main`
- [x] 产出 `apps/desktop/src-tauri/binaries/infinite-canvas-{target-triple}`
- [x] `sidecar.rs`：debug → `uv run`；release → `app.shell().sidecar("infinite-canvas")`
- [x] `beforeBuildCommand`：web build + sidecar build
- [x] `pnpm desktop:build` / `pnpm --filter desktop build:sidecar`
- [x] `capabilities/default.json`：`shell:allow-spawn` sidecar 权限
- [x] 签名命令模板（文档，不强制实际签名）

## Batch 2 defer

- 实际 codesign / notarization 密钥与 CI 密钥库配置
- 单实例锁、deep-link、自动更新
- Windows 交叉编译 sidecar（须在 Windows 主机执行 `build-sidecar.ps1`）
- Playwright 驱动 Tauri GUI

## 开发启动

```bash
uv sync --group dev && pnpm install
pnpm desktop:dev          # debug：uv sidecar
pnpm --filter desktop build:sidecar   # 仅打包 Python sidecar
pnpm desktop:build        # release 全链路（web + sidecar + Tauri）
```

## 手动验证清单

| # | 步骤 | 预期 |
|---|------|------|
| 1 | 仓库根 `pnpm desktop:dev` | Tauri 窗口打开，无 sidecar 启动报错 |
| 2 | 观察终端 / 活动监视器 | debug 存在 `uv run infinite-canvas` 子进程 |
| 3 | 应用内打开设置或首页 | API 请求成功（非 CORS / 连接拒绝） |
| 4 | `curl http://127.0.0.1:3000/api/app-info`（或实际端口） | HTTP 200 |
| 5 | 关闭主窗口 | sidecar 进程被 kill |
| 6 | 再次启动，托盘选「退出」 | 应用与 sidecar 均退出 |
| 7 | `pnpm --filter web build` | 前端构建仍通过 |
| 8 | `./scripts/build-sidecar.sh` | 产出平台二进制 |
| 9 | release 二进制 `./apps/desktop/src-tauri/binaries/infinite-canvas-* --port 3001 --data-dir /tmp/ic-test` + curl | `/api/app-info` 200 |

### 端口与数据目录

- 端口：从 **3000** 递增绑定 `127.0.0.1`
- dev 数据：`./.infinite-canvas-dev`
- prod macOS：`~/Library/Application Support/infinite-canvas/`

### 进程残留检查

```bash
# macOS / Linux
pgrep -fl "infinite-canvas|uvicorn"

# 关窗后应无 infinite-canvas 相关进程
```

## 自动化测试

`tests/e2e/desktop-sidecar.spec.ts` 为 **stub**：CI 默认不跑 Tauri GUI。

可选本地：

```bash
# 需图形环境 + 已安装 Tauri 依赖
pnpm desktop:dev  # 手动验证为主
```

## Batch 2 — 代码签名模板（文档）

> 实际签名需 Apple Developer / Windows 代码签名证书；CI 须通过 secrets 注入，**本批不配置密钥**。

### macOS codesign + notarization

```bash
# 1. 对 sidecar 二进制签名（在 tauri build 前或 build 后 re-sign 整个 .app）
SIDEcar="apps/desktop/src-tauri/binaries/infinite-canvas-$(rustc -vV | awk '/host:/ {print $2}')"
codesign --force --options runtime --sign "Developer ID Application: YOUR NAME (TEAMID)" "$SIDEcar"

# 2. tauri build 产出 .app / .dmg 后，对 app bundle 签名
APP="apps/desktop/src-tauri/target/release/bundle/macos/Infinite Canvas.app"
codesign --force --deep --options runtime --sign "Developer ID Application: YOUR NAME (TEAMID)" "$APP"

# 3. 公证（notarize）
ditto -c -k --keepParent "$APP" Infinite-Canvas.zip
xcrun notarytool submit Infinite-Canvas.zip \
  --apple-id "you@example.com" \
  --team-id "TEAMID" \
  --password "@keychain:AC_PASSWORD" \
  --wait
xcrun stapler staple "$APP"
```

### Windows Authenticode

```powershell
# sidecar（build-sidecar.ps1 产出后）
$Sidecar = "apps\desktop\src-tauri\binaries\infinite-canvas-x86_64-pc-windows-msvc.exe"
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /f "path\to\cert.pfx" /p "$env:SIGNING_PASSWORD" $Sidecar

# Tauri 安装包（build 后）
$Msi = "apps\desktop\src-tauri\target\release\bundle\msi\*.msi"
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /f "path\to\cert.pfx" /p "$env:SIGNING_PASSWORD" $Msi
```

### CI 注意事项

| 项 | 说明 |
|----|------|
| sidecar 平台 | **不可**在 macOS 上交叉编译 Windows sidecar；各 runner OS 分别跑 `build-sidecar.*` |
| 产物体积 | PyInstaller onefile 通常 50–150 MB；考虑 artifact 缓存与 Git LFS 策略 |
| 签名顺序 | sidecar 签名 → `tauri build` → 对最终 `.app`/`.msi`/`.exe` 再签名 |
| notarization | macOS Gatekeeper 要求 hardened runtime + notarize；dev 本地可 ad-hoc `-` 签名跳过 |
| secrets | `APPLE_ID`、`APPLE_TEAM_ID`、`APPLE_APP_PASSWORD`、`WINDOWS_CERT_PFX` 存 CI secrets |
| beforeBuildCommand | 已含 `build-sidecar.sh`；Windows CI 须改为 `build-sidecar.ps1` 或 matrix 条件脚本 |

## Batch 3 缺口

1. 实际 codesign / notarization / Authenticode 与 CI release workflow
2. Playwright 或 Rust integration test 覆盖 release sidecar
3. 单实例锁与深链接（设计规格 §7.3）
4. 自动更新（Tauri updater）
5. Windows runner 上 sidecar + MSI 全链路验证
