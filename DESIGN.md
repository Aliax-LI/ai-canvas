# DESIGN — 视觉设计规范

> **适用对象**：`apps/web` 全部 UI、Tauri 窗口 chrome、画布与智能画布。  
> **Agent 规则**：实现或修改界面时**必须**遵循本文件；不得擅自引入第二套色板或组件风格。  
> 关联文档：[`CONTEXT.md`](CONTEXT.md) · [`AGENTS.md`](AGENTS.md) · [架构设计规格](docs/superpowers/specs/2026-06-29-infinite-canvas-migration-desktop-design.md)

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **工具可信** | 像专业创作软件：清晰、稳定、低干扰，不花哨 |
| **双模式布局** | 导航/列表/设置 = **产品型**；无限画布编辑 = **工具型**（见 §3） |
| **parity 优先** | 视觉可现代化，**信息架构与操作路径**不得因改版而丢失能力 |
| **深浅色等价** | 所有页面、节点、面板在 light/dark 下均可用，对比度达标 |
| **Token 驱动** | 颜色/圆角/阴影只用 CSS 变量，禁止硬编码 `#hex`（画布预览图除外） |
| **桌面原生感** | Tauri 窗口：自定义标题栏、合理密度、支持键盘与快捷键 |

**气质参考**（借鉴不抄袭）：Linear、Figma、Raycast —— 中性底、细边框、轻阴影、强调色克制。

**与上游关系**：原 `coding/Infinite-Canvas/static/css/theme.css` 为对照；新 UI **更统一、更留白**，但保留「Studio + 画布」双层次记忆点。

---

## 2. 设计 Token（CSS 变量）

实现位置：`apps/web/src/styles/tokens.css`（由 Tailwind / shadcn 引用）。

### 2.1 色彩 — Light（`:root`）

| Token | 值 | 用途 |
|-------|-----|------|
| `--background` | `#FAFAFA` | 页面底 |
| `--foreground` | `#0A0A0B` | 主文字 |
| `--card` | `#FFFFFF` | 卡片、面板 |
| `--card-foreground` | `#0A0A0B` | 卡片文字 |
| `--muted` | `#F4F4F5` | 次要背景、输入底 |
| `--muted-foreground` | `#71717A` | 次要文字、说明 |
| `--border` | `#E4E4E7` | 分割线、边框 |
| `--input` | `#E4E4E7` | 输入框边框 |
| `--ring` | `#18181B` | 焦点环 |
| `--primary` | `#18181B` | 主按钮、关键强调 |
| `--primary-foreground` | `#FAFAFA` | 主按钮文字 |
| `--secondary` | `#F4F4F5` | 次要按钮 |
| `--secondary-foreground` | `#18181B` | 次要按钮文字 |
| `--accent` | `#F4F4F5` | hover、选中弱强调 |
| `--accent-foreground` | `#18181B` | accent 上文字 |
| `--destructive` | `#DC2626` | 删除、错误 |
| `--destructive-foreground` | `#FAFAFA` |  |
| `--success` | `#16A34A` | 成功、运行中 |
| `--warning` | `#D97706` | 警告、队列 |
| `--info` | `#2563EB` | 链接、信息 |

### 2.2 色彩 — Dark（`.dark`）

| Token | 值 | 用途 |
|-------|-----|------|
| `--background` | `#09090B` | 页面底 |
| `--foreground` | `#FAFAFA` | 主文字 |
| `--card` | `#111113` | 卡片、面板 |
| `--card-foreground` | `#FAFAFA` |  |
| `--muted` | `#18181B` | 次要背景 |
| `--muted-foreground` | `#A1A1AA` | 次要文字 |
| `--border` | `#27272A` | 边框 |
| `--input` | `#27272A` |  |
| `--ring` | `#D4D4D8` | 焦点环 |
| `--primary` | `#FAFAFA` | 主按钮（深色下反转） |
| `--primary-foreground` | `#18181B` |  |
| `--secondary` | `#27272A` |  |
| `--secondary-foreground` | `#FAFAFA` |  |
| `--accent` | `#27272A` |  |
| `--accent-foreground` | `#FAFAFA` |  |
| `--destructive` | `#EF4444` |  |
| `--success` | `#22C55E` |  |
| `--warning` | `#F59E0B` |  |
| `--info` | `#3B82F6` |  |

### 2.3 画布专用 Token

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `--canvas-bg` | `#F0F0F2` | `#0C0C0E` | 无限画布背景 |
| `--canvas-grid` | `rgba(0,0,0,.06)` | `rgba(255,255,255,.06)` | 点阵网格 |
| `--canvas-node-bg` | `#FFFFFF` | `#161618` | 节点卡片底 |
| `--canvas-node-border` | `#E4E4E7` | `#3F3F46` | 节点默认边框 |
| `--canvas-node-selected` | `#18181B` | `#FAFAFA` | 选中描边 |
| `--canvas-edge` | `#A1A1AA` | `#52525B` | 连线 |
| `--canvas-edge-active` | `#2563EB` | `#60A5FA` | 激活/data 流连线 |
| `--canvas-port` | `#71717A` | `#A1A1AA` | 端口 |
| `--canvas-minimap` | `rgba(255,255,255,.85)` | `rgba(17,17,19,.9)` | 小地图底 |

### 2.4 圆角、阴影、间距

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | `6px` | 标签、小按钮 |
| `--radius-md` | `8px` | 按钮、输入（**shadcn 默认 `--radius`**） |
| `--radius-lg` | `12px` | 卡片、对话框 |
| `--radius-xl` | `16px` | 大面板、智能画布卡片 |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,.05)` | 悬浮按钮 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,.08)` | 下拉、Popover |
| `--shadow-lg` | `0 12px 32px rgba(0,0,0,.12)` | 对话框、命令面板 |
| `--spacing-page` | `24px` | 产品型页面内边距 |
| `--spacing-panel` | `16px` | 面板内边距 |
| `--spacing-dense` | `8px` | 工具型工具栏 |

### 2.5 Tailwind / shadcn 映射

`tailwind.config` 中 `colors` 全部指向上述 CSS 变量（shadcn 默认格式）。**禁止**在组件内写死 `bg-zinc-900` 等，除非对应 token 文档化。

---

## 3. 布局模式（B+ 双模式）

### 3.1 产品型 Shell（默认）

用于：`/`、`/canvases`、`/assets`、`/settings/*`、`/chat`、`/tools/*`

```
┌──────────────────────────────────────────────────────┐
│ [─□×] 可选：Tauri 自定义标题栏                        │
├────────┬─────────────────────────────────────────────┤
│ Side   │  Topbar（面包屑 + 全局动作）                  │
│ 64/    ├─────────────────────────────────────────────┤
│ 240px  │                                             │
│        │  Content（max-width 可选，列表/表单）         │
│ Nav    │                                             │
│        │                                             │
└────────┴─────────────────────────────────────────────┘
```

| 元素 | 规范 |
|------|------|
| 侧栏宽度 | 折叠 `64px` / 展开 `240px`，动画 `200ms ease` |
| 侧栏背景 | `--card`，右边框 `1px solid var(--border)` |
| 导航项 | 高度 `40px`，圆角 `--radius-md`；active = `--accent` + 字重 500 |
| 内容区 | 背景 `--background`，padding `--spacing-page` |
| 顶栏 | 高度 `56px`，sticky，底边框 |

### 3.2 工具型 Canvas（无限画布）

用于：`/canvas/:id`

```
┌──────────────────────────────────────────────────────┐
│ Canvas Topbar：返回 | 标题 | 保存状态 | 队列 | 日志   │
├──────────────────────────────────────────────────────┤
│ ┌ Quick Toolbar（可折叠，左/顶浮动）                    │
│ │                                                      │
│ │            Infinite Canvas（@xyflow/react）           │
│ │                                                      │
│ └──────────────────────────────────────────────────────┤
│ 可选：右侧 Inspector 抽屉（节点属性，宽 320px）          │
└──────────────────────────────────────────────────────┘
```

| 元素 | 规范 |
|------|------|
| 顶栏 | 高度 `48px`，背景 `--card/80%` + `backdrop-blur` |
| 快捷工具栏 | 背景 `--card`，边框 `--border`，`shadow-md`，图标按钮 `32×32` |
| 画布区 | 占满剩余空间，背景 `--canvas-bg` |
| Inspector | Sheet 或固定右栏，宽 `320px`，滚动独立 |

### 3.3 智能画布

用于：`/smart/:id`

- 布局：**产品型顶栏** + **卡片网格/自由布局**（非节点图）
- 卡片：圆角 `--radius-xl`，边框 `--border`，hover `shadow-md`
- 卡片选中：边框 `2px solid var(--canvas-node-selected)`
- 连接指示：与无限画布共用 `--canvas-edge-active`

---

## 4.  typography

| 级别 | 字体 | 大小 / 行高 | 字重 | 用途 |
|------|------|-------------|------|------|
| `font-sans` | **Inter**，fallback 系统 UI | — | — | 全局 UI |
| `font-mono` | **JetBrains Mono**, ui-monospace | — | — | API Key、路径、日志 |
| Display | Inter | `24px / 32px` | 600 | 页面标题 |
| H1 | Inter | `20px / 28px` | 600 | 区块标题 |
| H2 | Inter | `16px / 24px` | 600 | 卡片标题 |
| Body | Inter | `14px / 20px` | 400 | 正文（**默认**） |
| Small | Inter | `12px / 16px` | 400 | 辅助说明、时间戳 |
| Tiny | Inter | `11px / 14px` | 500 | 徽章、标签 |

- 中文：Inter 缺字时 fallback `"PingFang SC"`, `"Microsoft YaHei"`, sans-serif  
- **最小正文 12px**；画布节点标题可用 13px  
- 数字/状态：tabular-nums

---

## 5. 组件规范（shadcn/ui）

| 场景 | 组件 | 变体 / 说明 |
|------|------|-------------|
| 主操作 | `Button` | `default` 主按钮；画布内 `secondary` / `ghost` 为主 |
| 危险 | `Button` | `destructive` |
| 表单 | `Input`, `Textarea`, `Select`, `Switch`, `Label` | 标签在上，间距 `8px` |
| 设置分组 | `Card` + `CardHeader` + `CardContent` | 组间距 `24px` |
| 侧栏设置 | `Tabs` | 竖向或横向，与 api/comfyui 设置一致 |
| 确认 | `AlertDialog` | 删除画布、清空队列 |
| 轻反馈 | `Sonner` toast | 成功 3s，错误 5s，可手动关闭 |
| 命令 | `Command` | `Cmd+K` / `Ctrl+K` 全局面板 |
| 节点属性 | `Sheet` | 右侧滑出，宽 320px |
| 素材预览 | `Dialog` | 大图预览，max 90vw |
| 列表 | `Table` 或虚拟列表 | 素材库、历史 |
| 加载 | `Skeleton` | 列表与卡片占位 |
| 空状态 | 自定义 `EmptyState` | 插画可选 Lucide 图标 + 一句说明 + 主按钮 |

**图标**：Lucide React，描边 `1.5`，默认 `16px`，工具栏 `18px`，侧栏 `20px`。

**按钮尺寸**：默认 `h-9 px-4`；dense 工具栏 `h-8 px-2`；图标按钮 `size-8` 或 `size-9`。

---

## 6. 无限画布节点视觉

### 6.1 节点通用

| 属性 | 值 |
|------|-----|
| 最小宽度 | `200px` |
| 内边距 | `12px` |
| 圆角 | `--radius-lg` |
| 背景 | `--canvas-node-bg` |
| 边框 | `1px solid var(--canvas-node-border)` |
| 选中 | `2px solid var(--canvas-node-selected)` + 轻 `shadow-md` |
| 运行中 | 左边框 `3px solid var(--info)` + 脉冲动画（可选） |
| 错误 | 左边框 `3px solid var(--destructive)` |
| 标题 | `Small` 字级，字重 600，单行 ellipsis |
| 端口 | 直径 `10px`，hover 放大至 `12px` |

### 6.2 节点类型色条（左侧 3px accent，非整卡上色）

| 类型 | 色条 |
|------|------|
| 图片 | `#71717A` |
| 提示词 | `#52525B` |
| API / 在线生图 | `#2563EB` |
| ModelScope | `#7C3AED` |
| ComfyUI | `#059669` |
| RunningHub | `#D97706` |
| LLM | `#0891B2` |
| 视频 | `#DB2777` |
| 输出 | `#18181B` / dark `#FAFAFA` |
| 循环 | `#CA8A04` |

### 6.3 连线

- 默认：贝塞尔，stroke `2px`，`--canvas-edge`
- 选中/数据流：`--canvas-edge-active`，stroke `2.5px`
- 动画流：stroke-dashoffset 动画（运行中任务）

### 6.4 画布背景

- 点阵网格，间距 `20px`（缩放自适应）
- 缩放控件：右下角，与 minimap 相邻
- Minimap：宽 `180px`，高 `120px`，圆角 `--radius-md`

---

## 7. 智能画布卡片

| 元素 | 规范 |
|------|------|
| 卡片间距 | `16px`（网格）或自由拖放 |
| 缩略图 | 圆角 `--radius-md`，比例保持，object-cover |
| 操作条 | hover 显示，顶栏 ghost 按钮 |
| @ 素材引用 | 药丸标签，`--muted` 底，圆角 full |
| 循环高亮 | 外发光 `0 0 0 2px var(--info)` |

---

## 8. 动效

| 场景 | 参数 |
|------|------|
| 页面切换 | Framer Motion，`opacity + y: 4`，`150ms`，`ease-out` |
| 侧栏折叠 | width `200ms ease` |
| Dialog / Sheet | shadcn 默认 + 不自定义过慢 |
| 节点选中 | scale 无；仅边框/阴影变化 `100ms` |
| 队列运行 | 顶栏指示点 pulse，`1.5s` |
| **减少动效** | 尊重 `prefers-reduced-motion`，关闭非必要动画 |

---

## 9. 状态与反馈

| 状态 | 视觉 |
|------|------|
| 空闲 | 默认 |
| 加载 | 按钮 spinner / 节点内 Skeleton |
| 运行中 | `--info` 指示 + 队列数字 |
| 成功 | toast success + 节点边框短暂 `--success` |
| 失败 | toast destructive + 日志面板可展开详情 |
| 离线 / API 不可用 | 顶栏 `Banner` `--warning` 底 |

---

## 10. 桌面端（Tauri）chrome

| 元素 | 规范 |
|------|------|
| 窗口 | 默认 `1280×800`，最小 `1024×640` |
| 标题栏 | 自定义时高 `32px`（Win）/ 与 traffic light 对齐（Mac） |
| 背景 | 与 `--background` 一致，避免 WebView 白闪 |
| 拖拽区 | 顶栏空白区 `-webkit-app-region: drag`；按钮 no-drag |
| 托盘 | 单色 Lucide 风格图标，与侧栏 logo 一致 |

---

## 11. 国际化与密度

- 文案：简中默认，键值 i18n（迁移原 `static/js/i18n/*` 语义）
- 按钮/标签：**预留 30% 英文变长空间**，避免固定宽 truncate
- 表单 label 统一顶部对齐，不采用 placeholder-only

---

## 12. 无障碍

- 正文对比度 ≥ **4.5:1**（WCAG AA）
- 焦点可见：ring `2px var(--ring)` offset `2px`
- 画布节点：选中态不仅靠颜色，必有边框宽度变化
- 图标按钮必须 `aria-label`

---

## 13. 禁止事项

- ❌ 引入第二套 UI 库（MUI、Ant Design 等）
- ❌ 画布节点大面积渐变 / 霓虹（干扰预览图）
- ❌ 硬编码颜色（`#333`、`text-gray-500` 未走 token）
- ❌ 产品型 Shell 与画布工具栏组件风格不一致
- ❌ 为「好看」删掉 parity 必需的控制项

---

## 14. 实现检查清单（PR / Agent 自检）

- [ ] 使用 `tokens.css` 变量，无 stray hex
- [ ] Light / dark 均已目视或 Storybook 截图
- [ ] 产品型 vs 工具型布局用对 Shell
- [ ] shadcn 组件未 heavily override 破坏一致性
- [ ] Lucide 图标尺寸符合 §5
- [ ] 画布节点符合 §6 色条与端口规范
- [ ] 键盘焦点与 `aria-label` 已补
- [ ] 未引入 scope 外视觉风格

---

## 15. 文件约定

```
apps/web/src/
├── styles/
│   ├── tokens.css          # §2 Token
│   └── globals.css         # tailwind base + shadcn
├── components/ui/          # shadcn 生成
├── components/shell/       # AppShell, Sidebar, Topbar
├── components/canvas/      # 节点、边、Minimap
└── features/               # 业务页（只用 shell + ui + canvas 组件）
```

**变更 Token 或布局模式时**：同步更新本 `DESIGN.md`，并在 `CONTEXT.md` §3 追加记录。
