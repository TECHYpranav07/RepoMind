import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Loader2 } from "lucide-react";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{eyebrow}</div>}
        <h1 className="text-balance text-2xl font-semibold tracking-tight md:text-[28px]">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {actions}
    </header>
  );
}

export function Section({
  title,
  description,
  children,
  className,
  actions,
}: {
  title?: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <section className={cn("rounded-xl border border-border bg-card", className)}>
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-tight">{title}</h2>}
            {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <code className={cn("rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[0.82em] text-foreground/90", className)}>
      {children}
    </code>
  );
}

/** Pages need a loaded repository, exactly like the original app. */
export function RequireRepo({ children }: { children: ReactNode }) {
  const { summary, summaryError, connection } = useWorkspace();
  if (summaryError) {
    return (
      <div className="mx-auto mt-16 max-w-md rounded-xl border border-border bg-card p-6 text-center">
        <h2 className="font-semibold">Can't reach RepoMind</h2>
        <p className="mt-2 text-sm text-muted-foreground">{summaryError}</p>
        <p className="mt-3 text-xs text-muted-foreground">
          {connection.mode === "live" ? "Start the server, or switch to the built-in sample from the sidebar." : null}
        </p>
      </div>
    );
  }
  if (!summary) {
    return (
      <div className="mt-24 flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading repository…
      </div>
    );
  }
  if (!summary.repo_loaded) {
    return (
      <div className="mx-auto mt-16 max-w-md rounded-xl border border-border bg-card p-6 text-center">
        <h2 className="font-semibold">No repository loaded</h2>
        <p className="mt-2 text-sm text-muted-foreground">Ingest a repository from the dashboard first.</p>
        <Link
          to="/"
          className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Go to dashboard <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    );
  }
  return <>{children}</>;
}

export function ModeBadge({ mode, className }: { mode: "graph" | "hybrid" | "ast"; className?: string }) {
  const map = {
    graph: "border-mode-graph/30 bg-mode-graph/10 text-mode-graph",
    hybrid: "border-mode-hybrid/30 bg-mode-hybrid/10 text-mode-hybrid",
    ast: "border-mode-ast/30 bg-mode-ast/10 text-mode-ast",
  } as const;
  const label = { graph: "GraphRAG", hybrid: "Hybrid GraphRAG", ast: "Deterministic AST ground truth" }[mode];
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium", map[mode], className)}>
      {label}
    </span>
  );
}
