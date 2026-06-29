import { Link, useLocation } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { breadcrumbsFromPathname } from "@/lib/navigation";
import { applyTheme, getStoredTheme, setStoredTheme, type Theme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export function Topbar() {
  const { pathname } = useLocation();
  const crumbs = breadcrumbsFromPathname(pathname);
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  function handleThemeToggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setStoredTheme(next);
    applyTheme(next);
    setTheme(next);
  }

  return (
    <header
      data-testid="app-topbar"
      className="sticky top-0 z-10 flex h-14 shrink-0 items-center justify-between border-b border-border bg-background/95 px-page backdrop-blur supports-[backdrop-filter]:bg-background/80"
    >
      <nav aria-label="面包屑" className="flex min-w-0 items-center gap-1 text-sm text-muted-foreground">
        {crumbs.map((crumb, index) => (
          <span key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-1">
            {index > 0 && <span className="text-muted-foreground/60">/</span>}
            {crumb.href ? (
              <Link to={crumb.href} className="truncate hover:text-foreground">
                {crumb.label}
              </Link>
            ) : (
              <span className={cn("truncate", index === crumbs.length - 1 && "font-medium text-foreground")}>
                {crumb.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <Button
        variant="ghost"
        size="icon"
        onClick={handleThemeToggle}
        aria-label={theme === "dark" ? "切换到浅色模式" : "切换到深色模式"}
        data-testid="theme-toggle"
      >
        {theme === "dark" ? (
          <Sun className="size-5" strokeWidth={1.5} />
        ) : (
          <Moon className="size-5" strokeWidth={1.5} />
        )}
      </Button>
    </header>
  );
}
