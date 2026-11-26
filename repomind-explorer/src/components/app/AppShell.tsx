import { useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { BarChart3, Home, Menu, MessageSquare, Network, Settings2, Sparkles, X } from "lucide-react";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";
import { ConnectionDialog } from "./ConnectionDialog";

const NAV = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/explorer", label: "Repository Explorer", icon: Network },
  { to: "/chat", label: "Repository Chat", icon: MessageSquare },
  { to: "/whatif", label: "What-If Analysis", icon: Sparkles },
  { to: "/evaluation", label: "Evaluation & Benchmark", icon: BarChart3 },
] as const;

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <circle cx="9" cy="10" r="3.2" className="fill-signal" />
        <circle cx="23" cy="8" r="2.4" className="fill-foreground/70" />
        <circle cx="21" cy="23" r="3.6" className="fill-foreground" />
        <circle cx="8" cy="23" r="2" className="fill-foreground/50" />
        <path d="M9 10 L23 8 M9 10 L21 23 M23 8 L21 23 M8 23 L21 23" className="stroke-foreground/35" strokeWidth="1.2" fill="none" />
      </svg>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">RepoMind</div>
        <div className="text-[11px] text-muted-foreground">Explainable GraphRAG</div>
      </div>
    </div>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const { summary, connection } = useWorkspace();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-6 pt-5">
        <Logo />
      </div>
      <nav className="flex flex-col gap-0.5 px-3">
        {NAV.map((n) => {
          const active = n.to === "/" ? pathname === "/" : pathname.startsWith(n.to);
          return (
            <Link
              key={n.to}
              to={n.to}
              onClick={onNavigate}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active ? "bg-sidebar-accent text-foreground" : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              <n.icon className={cn("h-4 w-4", active ? "text-signal" : "opacity-70")} />
              {n.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-8 px-5">
        <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Loaded repo</div>
        {summary?.repo_loaded ? (
          <div className="mt-2">
            <div className="truncate font-mono text-[13px] text-foreground">{summary.meta?.name}</div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground">
              {summary.nodes} nodes · {summary.chunks} chunks
            </div>
          </div>
        ) : (
          <div className="mt-2 text-xs text-muted-foreground">No repository loaded.</div>
        )}
      </div>

      <div className="mt-auto space-y-4 p-4">
        <button
          type="button"
          onClick={() => setOpen(true)}
          suppressHydrationWarning
          className="flex w-full items-center gap-3 rounded-lg border border-sidebar-border bg-background/40 px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent"
        >
          <span className="relative flex h-2 w-2">
            <span
              className={cn(
                "absolute inline-flex h-full w-full rounded-full opacity-60",
                connection.mode === "live" ? "animate-ping bg-success" : "bg-warning",
              )}
            />
            <span className={cn("relative inline-flex h-2 w-2 rounded-full", connection.mode === "live" ? "bg-success" : "bg-warning")} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-xs font-medium">{connection.mode === "live" ? "Live engine" : "Built-in sample"}</span>
            <span className="block truncate font-mono text-[10.5px] text-muted-foreground">
              {connection.mode === "live" ? connection.url.replace(/^https?:\/\//, "") : "Recorded RagCraft results"}
            </span>
          </span>
          <Settings2 className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
        <p className="px-1 text-[11px] leading-relaxed text-muted-foreground/80">
          RepoMind GraphRAG v1.0 · NetworkX AST, FAISS & multi-model LLM reasoning.
        </p>
      </div>
      <ConnectionDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-sidebar-border bg-sidebar lg:block">
        <SidebarBody />
      </aside>

      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-background/85 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button type="button" aria-label="Open menu" onClick={() => setMobileOpen(true)} className="rounded-md p-2 hover:bg-accent">
          <Menu className="h-5 w-5" />
        </button>
      </div>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-background/70 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border bg-sidebar">
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4 rounded-md p-1.5 hover:bg-accent"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarBody onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8 md:px-8 md:py-10">{children}</div>
      </main>
    </div>
  );
}
