import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, PanelLeft } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { mainNavGroups } from "@/lib/navigation";

const SIDEBAR_EXPANDED_KEY = "studio_sidebar_expanded";

function readExpanded(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_EXPANDED_KEY) !== "false";
  } catch {
    return true;
  }
}

export function Sidebar() {
  const [expanded, setExpanded] = useState(readExpanded);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_EXPANDED_KEY, String(expanded));
    } catch {
      // ignore
    }
  }, [expanded]);

  return (
    <aside
      data-testid="app-sidebar"
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border bg-card transition-[width] duration-200 ease-in-out",
        expanded ? "w-60" : "w-16",
      )}
      style={{ width: expanded ? 240 : 64 }}
    >
      <div className="flex h-14 items-center justify-between border-b border-border px-3">
        <div className={cn("flex items-center gap-2 overflow-hidden", !expanded && "justify-center w-full")}>
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md border-2 border-foreground text-xs font-semibold">
            AI
          </div>
          {expanded && <span className="truncate text-sm font-semibold">AI Studio</span>}
        </div>
        {expanded && (
          <Button
            variant="ghost"
            size="icon"
            className="size-8 shrink-0"
            onClick={() => setExpanded(false)}
            aria-label="折叠侧栏"
          >
            <ChevronLeft className="size-5" strokeWidth={1.5} />
          </Button>
        )}
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto p-2">
        {mainNavGroups.map((group) => (
          <div key={group.label}>
            {expanded && (
              <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {group.label}
              </p>
            )}
            <ul className="space-y-1">
              {group.items.map((item) => (
                <li key={item.href}>
                  <NavLink
                    to={item.href}
                    end={item.href === "/"}
                    className={({ isActive }) =>
                      cn(
                        "flex h-10 items-center gap-3 rounded-md px-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                        isActive && "bg-accent font-medium text-accent-foreground",
                        !expanded && "justify-center px-0",
                      )
                    }
                    title={!expanded ? item.title : undefined}
                  >
                    <item.icon className="size-5 shrink-0" strokeWidth={1.5} aria-hidden />
                    {expanded && <span className="truncate">{item.title}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {!expanded && (
        <div className="border-t border-border p-2">
          <Button
            variant="ghost"
            size="icon"
            className="size-10 w-full"
            onClick={() => setExpanded(true)}
            aria-label="展开侧栏"
          >
            <PanelLeft className="size-5" strokeWidth={1.5} />
          </Button>
        </div>
      )}
    </aside>
  );
}

export function SidebarCollapseHint() {
  return <ChevronRight className="size-4" strokeWidth={1.5} />;
}
