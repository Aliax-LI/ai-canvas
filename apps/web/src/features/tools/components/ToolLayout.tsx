import type { ReactNode } from "react";

interface ToolLayoutProps {
  title: string;
  subtitle?: string;
  testId?: string;
  controls: ReactNode;
  result?: ReactNode;
  history?: ReactNode;
}

export function ToolLayout({ title, subtitle, testId, controls, result, history }: ToolLayoutProps) {
  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-12" data-testid={testId}>
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-4 rounded-xl border border-border bg-card p-4">{controls}</aside>
        <section className="space-y-6">
          {result}
          {history}
        </section>
      </div>
    </div>
  );
}
