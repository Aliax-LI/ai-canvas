import { cn } from "@/lib/utils";
import type { ApiProvider } from "../types";

interface ProviderListProps {
  providers: ApiProvider[];
  selectedId: string;
  onSelect: (id: string) => void;
  onAdd: () => void;
}

export function ProviderList({ providers, selectedId, onSelect, onAdd }: ProviderListProps) {
  return (
    <div className="flex flex-col gap-2" data-testid="provider-list">
      <div className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">平台列表</div>
      <div className="flex flex-col gap-1">
        {providers.map((provider) => (
          <button
            key={provider.id}
            type="button"
            onClick={() => onSelect(provider.id)}
            className={cn(
              "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors",
              selectedId === provider.id
                ? "bg-accent font-medium text-accent-foreground"
                : "hover:bg-muted/80",
            )}
          >
            <span className="truncate">{provider.name || provider.id}</span>
            {provider.primary ? (
              <span className="ml-2 shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                默认
              </span>
            ) : null}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={onAdd}
        className="mt-1 flex items-center justify-center gap-2 rounded-md border border-dashed border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
      >
        新增平台
      </button>
    </div>
  );
}
