import { Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { HistoryItem } from "../types";

interface HistoryMasonryProps {
  items: HistoryItem[];
  loading?: boolean;
  onDelete?: (timestamp: number) => void;
}

export function HistoryMasonry({ items, loading, onDelete }: HistoryMasonryProps) {
  if (loading) {
    return (
      <div className="flex justify-center py-8 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  if (!items.length) {
    return <p className="py-8 text-center text-sm text-muted-foreground">暂无历史记录</p>;
  }

  return (
    <div>
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">历史记录</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        {items.map((item) => (
          <div
            key={item.timestamp}
            className="group relative aspect-square overflow-hidden rounded-xl border border-border bg-muted"
          >
            {item.images[0] ? (
              <img src={item.images[0]} alt="" className="size-full object-cover" loading="lazy" />
            ) : null}
            {onDelete ? (
              <Button
                type="button"
                size="icon"
                variant="secondary"
                className="absolute right-2 top-2 size-7 opacity-0 transition-opacity group-hover:opacity-100"
                onClick={() => onDelete(item.timestamp)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            ) : null}
            {item.prompt ? (
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 opacity-0 transition-opacity group-hover:opacity-100">
                <p className="line-clamp-2 text-[10px] text-white">{item.prompt}</p>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
