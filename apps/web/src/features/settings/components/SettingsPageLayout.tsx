import type { ReactNode } from "react";

interface SettingsPageLayoutProps {
  title: string;
  description: string;
  status?: ReactNode;
  sidebar: ReactNode;
  children: ReactNode;
}

export function SettingsPageLayout({
  title,
  description,
  status,
  sidebar,
  children,
}: SettingsPageLayoutProps) {
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6" data-testid="settings-page">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
        </div>
        {status ? <div className="text-sm text-muted-foreground">{status}</div> : null}
      </header>

      <div className="grid min-h-[560px] grid-cols-1 gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">{sidebar}</aside>
        <main className="rounded-lg border border-border bg-card p-6">{children}</main>
      </div>
    </div>
  );
}
