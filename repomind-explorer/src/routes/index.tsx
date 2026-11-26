import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertCircle, CheckCircle2, GitBranch, Loader2, Rocket, Star, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { PageHeader, Section } from "@/components/app/Page";
import { NODE_COLORS, EDGE_COLORS } from "@/lib/repomind/graph-style";
import { useWorkspace } from "@/lib/repomind/workspace";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RepoMind — Dashboard" },
      { name: "description", content: "Ingest a GitHub repository and see its knowledge-graph architecture metrics." },
      { property: "og:title", content: "RepoMind — Dashboard" },
      { property: "og:description", content: "Ingest a GitHub repository and see its knowledge-graph architecture metrics." },
    ],
  }),
  component: Dashboard,
});

const FORMATS = [
  { label: "Python AST (.py)", color: NODE_COLORS.Repository },
  { label: "Markdown docs (.md)", color: NODE_COLORS.Class },
  { label: "Dependencies (.txt, .toml)", color: NODE_COLORS.Function },
  { label: "Configurations (.yaml, .cfg)", color: NODE_COLORS.Library },
];

function Dashboard() {
  const { summary, ingest, runIngest } = useWorkspace();
  const [repoInput, setRepoInput] = useState("sample_repo");
  const loaded = summary?.repo_loaded;

  const analyze = (target: string) => {
    if (!target.trim() || ingest.running) return;
    void runIngest(target.trim());
  };

  return (
    <>
      <PageHeader
        eyebrow="RepoMind"
        title="Understand how your code is connected — and what breaks when it changes."
        description="Explainable GraphRAG for software repository what-if change-impact analysis."
      />

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Section title="Ingest repository" description="Enter a public GitHub repository URL, or explore the built-in reference architecture.">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              analyze(repoInput);
            }}
            className="space-y-3"
          >
            <label htmlFor="repo" className="text-xs text-muted-foreground">
              GitHub repository URL or shorthand (e.g. <span className="font-mono">owner/repo</span>)
            </label>
            <Input
              id="repo"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              placeholder="e.g. TECHYpranav07/RepoMind or sample_repo"
              className="h-11 font-mono text-sm"
              suppressHydrationWarning
            />

            <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground pt-1">
              <span className="text-[11px] font-medium">Quick presets:</span>
              {[
                { label: "⚡ Built-in RagCraft", val: "sample_repo" },
                { label: "🧠 RepoMind Core", val: "TECHYpranav07/RepoMind" },
                { label: "🔬 AMR Explainable", val: "Amitmali72/amr-explainable" },
                { label: "🌐 FastAPI", val: "tiangolo/fastapi" },
              ].map((p) => (
                <button
                  key={p.val}
                  type="button"
                  onClick={() => {
                    setRepoInput(p.val);
                    analyze(p.val);
                  }}
                  className="rounded-md border border-border bg-accent/40 px-2 py-1 text-[11px] font-mono hover:bg-accent hover:text-foreground transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="submit" className="h-10 flex-1" disabled={ingest.running || !repoInput.trim()}>
                {ingest.running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
                Analyze repository
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="h-10 flex-1"
                disabled={ingest.running}
                onClick={() => {
                  setRepoInput("sample_repo");
                  analyze("sample_repo");
                }}
              >
                <Zap className="h-4 w-4" /> Load built-in RagCraft repo
              </Button>
            </div>
          </form>

          {(ingest.running || ingest.progress) && !ingest.error && (
            <div className="mt-5 space-y-2">
              <Progress value={(ingest.progress?.progress ?? 0) * 100} className="h-1.5" />
              <p className="font-mono text-xs text-muted-foreground">{ingest.progress?.message}</p>
            </div>
          )}
          {ingest.success && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2.5 text-sm text-success">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> {ingest.success}
            </div>
          )}
          {ingest.error && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2.5 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {ingest.error}
            </div>
          )}
        </Section>

        <Section title="Engine status">
          {loaded ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-success" />
                <span className="text-sm">
                  Active: <span className="font-mono font-medium">{summary.meta?.full_name}</span>
                </span>
              </div>
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <GitBranch className="h-3.5 w-3.5" /> <span className="font-mono">{summary.meta?.default_branch}</span>
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Star className="h-3.5 w-3.5" /> {summary.meta?.stars}
                </span>
              </div>
              {summary.meta?.description && <p className="text-xs leading-relaxed text-muted-foreground">{summary.meta.description}</p>}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No repository currently loaded in memory.</p>
          )}
          <div className="mt-5 border-t border-border pt-4">
            <div className="mb-2.5 text-xs font-medium text-muted-foreground">Supported formats</div>
            <div className="flex flex-wrap gap-1.5">
              {FORMATS.map((f) => (
                <span key={f.label} className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11.5px]">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: f.color }} />
                  {f.label}
                </span>
              ))}
            </div>
          </div>
        </Section>
      </div>

      {loaded && (
        <div className="mt-10">
          <h2 className="mb-4 text-sm font-semibold tracking-tight">Repository architecture metrics</h2>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-5">
            {[
              ["Indexed files", summary.files],
              ["Vector chunks", summary.chunks],
              ["Graph nodes", summary.nodes],
              ["Graph edges", summary.edges],
              ["Lines of code", summary.lines_of_code],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-card px-5 py-5">
                <div className="font-mono text-3xl font-medium tracking-tight">{(val as number)?.toLocaleString()}</div>
                <div className="mt-1 text-xs text-muted-foreground">{label}</div>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <Section title="Entity breakdown">
              <Breakdown data={summary.node_type_breakdown ?? {}} colors={NODE_COLORS} empty="No entity breakdown available." />
            </Section>
            <Section title="Relationship breakdown">
              <Breakdown data={summary.edge_relation_breakdown ?? {}} colors={EDGE_COLORS} mono empty="No relationship breakdown available." />
            </Section>
          </div>
        </div>
      )}
    </>
  );
}

function Breakdown({
  data,
  colors,
  mono,
  empty,
}: {
  data: Record<string, number>;
  colors: Record<string, string>;
  mono?: boolean;
  empty: string;
}) {
  const entries = Object.entries(data);
  if (!entries.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <ul className="space-y-2.5">
      {entries.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[130px_1fr_40px] items-center gap-3 text-sm">
          <span className={mono ? "font-mono text-xs" : ""}>{k}</span>
          <span className="h-1.5 overflow-hidden rounded-full bg-muted">
            <span
              className="block h-full rounded-full transition-[width] duration-700"
              style={{ width: `${(v / max) * 100}%`, background: colors[k] ?? "#94a3b8" }}
            />
          </span>
          <span className="text-right font-mono text-xs text-muted-foreground">{v}</span>
        </li>
      ))}
    </ul>
  );
}
