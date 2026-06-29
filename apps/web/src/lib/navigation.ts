import type { LucideIcon } from "lucide-react";
import {
  Home,
  LayoutGrid,
  Image,
  MessageSquare,
  Wand2,
  Sparkles,
  Pencil,
  RotateCcw,
  Globe,
  Settings,
  Cpu,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  description?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const mainNavGroups: NavGroup[] = [
  {
    label: "工作室",
    items: [
      { title: "首页", href: "/", icon: Home, description: "AI Studio 工作台" },
      { title: "无限画布", href: "/canvases", icon: LayoutGrid, description: "画布列表与管理" },
      { title: "素材库", href: "/assets", icon: Image, description: "资产与素材管理" },
      { title: "GPT 对话", href: "/chat", icon: MessageSquare, description: "多模型对话" },
    ],
  },
  {
    label: "本地功能",
    items: [
      { title: "文生图", href: "/tools/zimage", icon: Wand2, description: "Z-Image 文生图" },
      { title: "细节增强", href: "/tools/enhance", icon: Sparkles, description: "图片细节增强" },
      { title: "图片编辑", href: "/tools/klein", icon: Pencil, description: "Klein 图片编辑" },
      { title: "角度控制", href: "/tools/angle", icon: RotateCcw, description: "相机角度控制" },
    ],
  },
  {
    label: "在线",
    items: [
      { title: "在线生图", href: "/tools/online", icon: Globe, description: "云端 API 生图" },
    ],
  },
  {
    label: "设置",
    items: [
      { title: "API 设置", href: "/settings/api", icon: Settings, description: "API Key 与提供商" },
      { title: "ComfyUI", href: "/settings/comfyui", icon: Cpu, description: "ComfyUI 连接配置" },
    ],
  },
];

export const allNavItems: NavItem[] = mainNavGroups.flatMap((g) => g.items);

export interface BreadcrumbSegment {
  label: string;
  href?: string;
}

const routeLabels: Record<string, string> = {
  "": "首页",
  canvases: "无限画布",
  canvas: "画布编辑",
  smart: "智能画布",
  assets: "素材库",
  settings: "设置",
  api: "API 设置",
  comfyui: "ComfyUI",
  chat: "GPT 对话",
  tools: "工具",
  zimage: "文生图",
  enhance: "细节增强",
  klein: "图片编辑",
  online: "在线生图",
  angle: "角度控制",
};

export function breadcrumbsFromPathname(pathname: string): BreadcrumbSegment[] {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) {
    return [{ label: "首页" }];
  }

  const crumbs: BreadcrumbSegment[] = [{ label: "首页", href: "/" }];
  let path = "";

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    path += `/${segment}`;
    const isLast = i === segments.length - 1;
    const label = routeLabels[segment] ?? segment;

    if (segment === "canvas" || segment === "smart") {
      const next = segments[i + 1];
      crumbs.push({ label, href: isLast && !next ? undefined : path });
      if (next) {
        crumbs.push({ label: next });
      }
      break;
    }

    crumbs.push({ label, href: isLast ? undefined : path });
  }

  return crumbs;
}
