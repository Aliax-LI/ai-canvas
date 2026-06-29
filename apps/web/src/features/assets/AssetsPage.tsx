import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { uploadLocalAssets } from "@/lib/api/upload";
import { batchAddAssets, createAssetLibrary, deleteAssets, fetchAssetLibrary } from "./api";
import type { AssetCategory, AssetItem, AssetLibrary } from "./types";

export function AssetsPage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [libraryId, setLibraryId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const libraryQuery = useQuery({
    queryKey: ["asset-library"],
    queryFn: fetchAssetLibrary,
  });

  const root = libraryQuery.data;
  const libraries = root?.libraries ?? [];

  const activeLibrary: AssetLibrary | null = useMemo(() => {
    const id = libraryId || root?.active_library_id || libraries[0]?.id || "";
    return libraries.find((l) => l.id === id) ?? libraries[0] ?? null;
  }, [libraries, libraryId, root]);

  const imageCategories = useMemo(
    () => (activeLibrary?.categories ?? []).filter((c) => c.type === "image"),
    [activeLibrary],
  );

  const activeCategory: AssetCategory | null = useMemo(() => {
    const id = categoryId || imageCategories[0]?.id || "";
    return imageCategories.find((c) => c.id === id) ?? imageCategories[0] ?? null;
  }, [imageCategories, categoryId]);

  const items = useMemo(() => {
    const list = activeCategory?.items ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        (item.classification ?? "").toLowerCase().includes(q),
    );
  }, [activeCategory, query]);

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      if (!activeLibrary || !activeCategory) throw new Error("请先选择分类");
      const uploaded = await uploadLocalAssets(files);
      return batchAddAssets({
        library_id: activeLibrary.id,
        category_id: activeCategory.id,
        items: uploaded.files.map((f) => ({ url: f.url, name: f.name })),
      });
    },
    onSuccess: () => {
      toast.success("素材已上传");
      void queryClient.invalidateQueries({ queryKey: ["asset-library"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "上传失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      if (!activeLibrary) throw new Error("未选择资产库");
      return deleteAssets(ids, activeLibrary.id);
    },
    onSuccess: () => {
      setSelected(new Set());
      toast.success("已删除");
      void queryClient.invalidateQueries({ queryKey: ["asset-library"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "删除失败"),
  });

  const createLibMutation = useMutation({
    mutationFn: () => createAssetLibrary(`资产库 ${libraries.length + 1}`),
    onSuccess: () => {
      toast.success("资产库已创建");
      void queryClient.invalidateQueries({ queryKey: ["asset-library"] });
    },
  });

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (libraryQuery.isLoading) {
    return (
      <div className="flex justify-center py-24 text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" />
        加载素材库…
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[560px] flex-col gap-4" data-testid="assets-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">素材库</h1>
          <p className="text-sm text-muted-foreground">管理图片/视频/音频资产（核心资产库 Tab）</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="搜索素材…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-9 w-48"
          />
          <Button type="button" variant="outline" size="sm" onClick={() => createLibMutation.mutate()}>
            新建资产库
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending || !activeCategory}
          >
            {uploadMutation.isPending ? <Loader2 className="animate-spin" /> : <ImagePlus />}
            上传
          </Button>
          {selected.size > 0 ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => deleteMutation.mutate([...selected])}
            >
              <Trash2 />
              删除 ({selected.size})
            </Button>
          ) : null}
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        multiple
        accept="image/*,video/*,audio/*"
        className="hidden"
        onChange={(e) => {
          const files = [...(e.target.files ?? [])];
          if (files.length) uploadMutation.mutate(files);
          e.target.value = "";
        }}
      />

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[220px_180px_minmax(0,1fr)]">
        <aside className="rounded-lg border border-border bg-card p-3">
          <div className="mb-2 text-xs font-medium uppercase text-muted-foreground">资产库</div>
          <div className="flex flex-col gap-1">
            {libraries.map((lib) => (
              <button
                key={lib.id}
                type="button"
                onClick={() => {
                  setLibraryId(lib.id);
                  setCategoryId("");
                }}
                className={`rounded-md px-3 py-2 text-left text-sm ${
                  activeLibrary?.id === lib.id ? "bg-accent font-medium" : "hover:bg-muted/80"
                }`}
              >
                {lib.name}
              </button>
            ))}
          </div>
        </aside>

        <aside className="rounded-lg border border-border bg-card p-3">
          <div className="mb-2 text-xs font-medium uppercase text-muted-foreground">分类</div>
          <div className="flex flex-col gap-1">
            {imageCategories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategoryId(cat.id)}
                className={`rounded-md px-3 py-2 text-left text-sm ${
                  activeCategory?.id === cat.id ? "bg-accent font-medium" : "hover:bg-muted/80"
                }`}
              >
                {cat.name}
                <span className="ml-1 text-xs text-muted-foreground">({cat.items.length})</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="min-h-0 overflow-auto rounded-lg border border-border bg-card p-4">
          {!items.length ? (
            <p className="py-16 text-center text-sm text-muted-foreground">暂无素材，点击上传添加</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {items.map((item) => (
                <AssetTile
                  key={item.id}
                  item={item}
                  selected={selected.has(item.id)}
                  onToggle={() => toggleSelect(item.id)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function AssetTile({
  item,
  selected,
  onToggle,
}: {
  item: AssetItem;
  selected: boolean;
  onToggle: () => void;
}) {
  const isImage = item.kind === "image" || /\.(png|jpe?g|webp|gif)(\?|$)/i.test(item.url);

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`overflow-hidden rounded-lg border text-left transition-colors ${
        selected ? "border-primary ring-2 ring-primary/30" : "border-border hover:border-foreground/20"
      }`}
    >
      <div className="aspect-square bg-muted">
        {isImage ? (
          <img src={item.url} alt={item.name} className="size-full object-cover" loading="lazy" />
        ) : (
          <div className="flex size-full items-center justify-center text-xs text-muted-foreground">
            {item.kind ?? "file"}
          </div>
        )}
      </div>
      <div className="truncate px-2 py-2 text-xs font-medium">{item.name}</div>
    </button>
  );
}
