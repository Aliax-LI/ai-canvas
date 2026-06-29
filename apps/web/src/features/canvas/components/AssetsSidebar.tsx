import { useQuery } from "@tanstack/react-query";
import { ImageIcon, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchAssetLibrary } from "@/features/assets/api";
import { mediaPreviewUrl } from "../api";

interface AssetsSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAddImageNode: (url: string, name: string) => void;
}

export function AssetsSidebar({ open, onOpenChange, onAddImageNode }: AssetsSidebarProps) {
  const libraryQuery = useQuery({
    queryKey: ["asset-library"],
    queryFn: fetchAssetLibrary,
    enabled: open,
  });

  const root = libraryQuery.data;
  const libraries = root?.libraries ?? [];
  const activeLibrary =
    libraries.find((l) => l.id === root?.active_library_id) ?? libraries[0] ?? null;
  const imageCategories = (activeLibrary?.categories ?? []).filter((c) => c.type === "image");
  const items = imageCategories.flatMap((c) => c.items ?? []);

  if (!open) return null;

  return (
    <aside
      className="flex w-72 shrink-0 flex-col border-l border-border bg-card/95 backdrop-blur"
      data-testid="canvas-assets-sidebar"
    >
      <div className="flex h-10 items-center justify-between border-b border-border px-3">
        <span className="text-xs font-semibold">资产库</span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-7"
          onClick={() => onOpenChange(false)}
          aria-label="关闭资产库"
        >
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {libraryQuery.isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="mr-2 size-4 animate-spin" />
            加载中…
          </div>
        ) : items.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">暂无图片资产</p>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className="group overflow-hidden rounded-md border border-border bg-muted/30 text-left transition hover:border-primary"
                data-testid={`canvas-asset-item-${item.id}`}
                onClick={() => onAddImageNode(item.url, item.name)}
              >
                {item.url ? (
                  <img
                    src={mediaPreviewUrl(item.url, 160)}
                    alt={item.name}
                    className="aspect-square w-full object-cover"
                  />
                ) : (
                  <div className="flex aspect-square items-center justify-center bg-muted">
                    <ImageIcon className="size-6 text-muted-foreground" />
                  </div>
                )}
                <div className="truncate px-1.5 py-1 text-[10px] text-muted-foreground">
                  {item.name}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-border px-3 py-2">
        <p className="text-[10px] text-muted-foreground">
          点击资产创建图片节点；选中生成器时自动连线
        </p>
      </div>
    </aside>
  );
}

export function AssetsToggle({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Button
      type="button"
      variant={open ? "secondary" : "outline"}
      size="sm"
      className="h-8"
      data-testid="canvas-assets-toggle"
      onClick={onToggle}
    >
      <ImageIcon className="mr-1 size-3.5" />
      资产库
    </Button>
  );
}
