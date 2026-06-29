# M10 — Tauri 2 桌面端计划与验证清单

> 设计规格 §7 · Batch 1 完成壳层 + dev sidecar

## Batch 1 范围（本批）

- [x] `apps/desktop/` Tauri 2 scaffold
- [x] Rust sidecar：`uv run infinite-canvas`，端口 3000+ 自增，健康检查 60s
- [x] 关窗 / 退出 kill 子进程
- [x] 前端 API base 注入（`__INFINITE_CANVAS_API__` + Tauri invoke fallback）
- [x] 系统托盘：显示/隐藏、退出
- [x] `externalBin` 占位 + `scripts/build-sidecar.*`
- [x] E2E stub + 手动验证文档

## Batch 1 defer

- PyInstaller 实际二进制产出与 CI 集成
- codesign / notarization / Authenticode
- 单实例锁、deep-link、自动更新
- 无边框自定义标题栏
- prod 模式使用 bundled sidecar（当前 release 仍回退 uv）

## 开发启动

```bash
uv sync && pnpm install
pnpm desktop:dev
```

## 手动验证清单

| # | 步骤 | 预期 |
|---|------|------|
| 1 | 仓库根 `pnpm desktop:dev` | Tauri 窗口打开，无 sidecar 启动报错 |
| 2 | 观察终端 / 活动监视器 | 存在 `uv run infinite-canvas` 子进程 |
| 3 | 应用内打开设置或首页 | API 请求成功（非 CORS / 连接拒绝） |
| 4 | `curl http://127.0.0.1:3000/api/app-info`（或实际端口） | HTTP 200 |
| 5 | 关闭主窗口 | sidecar 进程被 kill |
| 6 | 再次启动，托盘选「退出」 | 应用与 sidecar 均退出 |
| 7 | `pnpm --filter web build` | 前端构建仍通过 |

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

## Batch 2 缺口

1. PyInstaller sidecar 二进制 + `tauri build` 全链路
2. prod 分支使用 `tauri_plugin_shell::Sidecar` 替代 uv
3. macOS / Windows 签名与安装包
4. Playwright 驱动 Tauri 或 Rust integration test
5. 单实例锁与深链接（设计规格 §7.3）
