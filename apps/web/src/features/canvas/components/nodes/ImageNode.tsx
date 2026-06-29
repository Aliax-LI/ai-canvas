import { ImageIcon } from "lucide-react";
import { mediaPreviewUrl } from "../../api";
import { BaseNodeShell, type CanvasNodeProps } from "../BaseNode";
import type { ImageNodeData } from "@infinite-canvas/canvas-schema";

export function ImageNode({ id, data, selected }: CanvasNodeProps<ImageNodeData>) {
  const url = String(data.url ?? "");
  const name = String(data.name ?? "空白图片");

  return (
    <BaseNodeShell
      type="image"
      title={name}
      selected={selected}
      data-testid={`canvas-node-${id}`}
    >
      {url ? (
        <img
          src={mediaPreviewUrl(url, 400)}
          alt={name}
          className="max-h-32 w-full rounded-md object-cover"
        />
      ) : (
        <div className="flex h-24 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <ImageIcon className="size-8" strokeWidth={1.5} />
        </div>
      )}
    </BaseNodeShell>
  );
}
