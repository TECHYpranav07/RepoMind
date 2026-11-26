import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ChevronDown, Download, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LatencyChart, ScoreChart } from "@/components/app/BenchmarkCharts";
import { Markdown } from "@/components/app/Markdown";
import { ModeBadge, PageHeader, RequireRepo } from "@/components/app/Page";
import { SearchSelect } from "@/components/app/SearchSelect";
import {
  asList,
  buildMatrix,
  fmtMetric,
  isNum,
  KPI_THRESHOLD,
  modeRow,
  pickWinner,
  rowsToCsv,
} from "@/lib/repomind/benchmark";
import { downloadText } from "@/lib/repomind/download";
import type { BenchmarkRow, ChatMode, GtSource, SpeedMode } from "@/lib/repomind/types";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/evaluation")({
  head: () => ({
    meta: [
      { title: "Evaluation & Benchmark — RepoMind" },
      { name: "description", content: "Benchmark GraphRAG vs Hybrid GraphRAG against deterministic AST ground truth." },
      { property: "og:title", content: "Evaluation & Benchmark — RepoMind" },
      { property: "og:description", content: "Benchmark GraphRAG vs Hybrid GraphRAG against deterministic AST ground truth." },
    ],
  }),
  component: () => (
    <RequireRepo>
      <Evaluation />
    </RequireRepo>
  ),
});

const MODE_CHOICES: { label: string; modes: ChatMode[] }[] = [
  { label: "Both (GraphRAG + Hybrid)", modes: ["graph", "hybrid"] },
  { label: "GraphRAG only", modes: ["graph"] },
  { label: "Hybrid only", modes: ["hybrid"] },
];

function Evaluation() {
  const { summary, client, benchmark, setBenchmark } = useWorkspace();
  const [gt, setGt] = useState<GtSource>("ast");
  const [speed, setSpeed] = useState<SpeedMode>("fast");
  const [modeIdx, setModeIdx] = useState(0);
  const [numQ, setNumQ] = useState(3);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ message: string; progress: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const choice = MODE_CHOICES[modeIdx];
    const modes = choice?.modes ?? [];
    if (!modes.length) return setError("Please select at least one retrieval mode.");
    setRunning(true);
    setError(null);
    setProgress({ message: "Starting…", progress: 0 });
    try {
      const rows = await client.runBenchmark({ modes, num_questions: numQ, gt_source: gt, speed_mode: speed }, setProgress);
      setBenchmark({ rows, lastRun: new Date(), status: "Success" });
      setProgress({ message: "Benchmark completed successfully!", progress: 1 });
    } catch (e) {
      setBenchmark({ ...benchmark, status: `Error: ${(e as Error).message}` });
      setError(`Benchmark failed: ${(e as Error).message}`);
      setProgress(null);
    } finally {
      setRunning(false);
    }
  };

  const rows = benchmark.rows;
  const lastRunText = benchmark.lastRun ? benchmark.lastRun.toTimeString().slice(0, 8) : "Not run yet";

  return (
    <>
      <PageHeader
        eyebrow="Evaluation & Benchmark"
        title="How well does each retrieval mode understand this repo?"
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span>
              Compare <ModeBadge mode="graph" /> vs <ModeBadge mode="hybrid" /> against <ModeBadge mode="ast" />
            </span>
            <span className="text-border">·</span>
            <span className="font-mono text-xs text-muted-foreground">
              {summary?.meta?.full_name ?? "Repo"} ({(summary?.nodes ?? 0).toLocaleString()} nodes) · Last run: {lastRunText}
            </span>
          </span>
        }
      />

      <div className="rounded-xl border border-border bg-card p-5">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Ground truth source">
            <Select value={gt} onValueChange={(v) => setGt(v as GtSource)}>
              <SelectTrigger className="h-10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ast">Live AST ground truth (auto-extracted from repo)</SelectItem>
                <SelectItem value="curated">Curated architecture golden set</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Execution engine">
            <Select value={speed} onValueChange={(v) => setSpeed(v as SpeedMode)}>
              <SelectTrigger className="h-10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fast">Fast parallel (Gemini Flash · 2-3s)</SelectItem>
                <SelectItem value="turbo">Instant turbo (local engine · &lt;1s)</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>
        <div className="mt-4 grid items-end gap-4 md:grid-cols-[1.6fr_0.6fr_0.8fr]">
          <Field label="Retrieval modes to test">
            <div className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-surface p-1">
              {MODE_CHOICES.map((m, i) => (
                <button
                  key={m.label}
                  type="button"
                  onClick={() => setModeIdx(i)}
                  className={cn(
                    "rounded-md px-2 py-1.5 text-xs transition-colors",
                    modeIdx === i ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Questions">
            <Input
              type="number"
              min={1}
              max={10}
              value={numQ}
              onChange={(e) => setNumQ(Math.min(10, Math.max(1, Number(e.target.value) || 1)))}
              className="h-10 font-mono"
            />
          </Field>
          <Button className="h-10" disabled={running} onClick={run}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? "Running…" : "Run benchmark"}
          </Button>
        </div>
        {progress && (
          <div className="mt-4 space-y-2">
            <Progress value={progress.progress * 100} className="h-1.5" />
            <p className={cn("font-mono text-xs", progress.progress >= 1 && !running ? "text-success" : "text-muted-foreground")}>
              {progress.message}
            </p>
          </div>
        )}
        {error && <p className="mt-4 text-sm text-danger">{error}</p>}
      </div>

      {!rows || rows.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="mt-8 space-y-8">
          <Kpis rows={rows} />
          <div>
            <SectionTitle>Performance visualizations</SectionTitle>
            <div className="grid gap-5 lg:grid-cols-2">
              <ScoreChart rows={rows} title="Retrieval quality" subtitle="Precision@K · Recall@K" metrics={[["precision_at_k", "Precision@K"], ["recall_at_k", "Recall@K"]]} />
              <ScoreChart
                rows={rows}
                title="Change impact detection"
                subtitle="Impact precision · recall · F1"
                metrics={[["impact_precision", "Impact Precision"], ["impact_recall", "Impact Recall"], ["impact_f1", "Impact F1"]]}
              />
              <ScoreChart rows={rows} title="Answer reliability" subtitle="Correctness · faithfulness" metrics={[["correctness", "Answer Correctness"], ["faithfulness", "Faithfulness"]]} />
              <LatencyChart rows={rows} />
            </div>
          </div>
          <Interpretation rows={rows} />
          <div className="space-y-3">
            <DeepDive rows={rows} />
            <DetailedResults rows={rows} />
          </div>
        </div>
      )}
      <div className="mt-3">
        <Glossary />
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs text-muted-foreground">{label}</div>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-4 text-sm font-semibold tracking-tight">{children}</h2>;
}

function EmptyState() {
  return (
    <div className="mt-8 rounded-xl border border-dashed border-border px-6 py-10 text-center">
      <h3 className="text-base font-semibold">Ready for ground-truth evaluation</h3>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">
        Click <span className="text-foreground font-medium">Run benchmark</span> above to test GraphRAG vs Hybrid GraphRAG using{" "}
        deterministic compiler facts extracted directly from this repository&apos;s AST.
      </p>
    </div>
  );
}

const KPIS = [
  { title: "Retrieval recall", metric: "recall_at_k", unit: "%" as const, desc: "% of relevant files retrieved", hib: true },
  { title: "Impact detection", metric: "impact_f1", unit: "%" as const, desc: "Accuracy predicting affected components", hib: true },
  { title: "Answer faithfulness", metric: "faithfulness", unit: "%" as const, desc: "% of answer grounded in code", hib: true },
  { title: "Response speed", metric: "total_latency_s", unit: "s" as const, desc: "End-to-end execution latency", hib: false },
];

function Kpis({ rows }: { rows: BenchmarkRow[] }) {
  const cols = KPIS.map((k) => k.metric);
  const g = modeRow(rows, "GRAPH", cols);
  const h = modeRow(rows, "HYBRID", cols);
  return (
    <div>
      <SectionTitle>Executive summary</SectionTitle>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {KPIS.map((k) => {
          const gv = g?.[k.metric];
          const hv = h?.[k.metric];
          const w = pickWinner(gv, hv, k.hib, k.unit === "s" ? KPI_THRESHOLD.latency : KPI_THRESHOLD.score);
          return (
            <div key={k.metric} className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{k.title}</span>
                {w && (
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                      w === "hybrid" && "bg-mode-hybrid/15 text-mode-hybrid",
                      w === "graph" && "bg-mode-graph/15 text-mode-graph",
                      w === "tie" && "bg-muted text-muted-foreground",
                    )}
                  >
                    {w === "tie" ? "Tied" : w === "hybrid" ? "Hybrid leads" : "Graph leads"}
                  </span>
                )}
              </div>
              <div className="mt-3 space-y-1.5">
                <KpiRow label="Graph" tone="graph" v={fmtMetric(gv, k.unit)} />
                <KpiRow label="Hybrid" tone="hybrid" v={fmtMetric(hv, k.unit)} />
              </div>
              <div className="mt-3 border-t border-border pt-2.5 text-[11px] text-muted-foreground">{k.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function KpiRow({ label, tone, v }: { label: string; tone: "graph" | "hybrid"; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className={cn("inline-flex items-center gap-1.5 text-xs", tone === "graph" ? "text-mode-graph" : "text-mode-hybrid")}>
        <span className={cn("h-1.5 w-1.5 rounded-full", tone === "graph" ? "bg-mode-graph" : "bg-mode-hybrid")} />
        {label}
      </span>
      <span className="font-mono text-lg">{v}</span>
    </div>
  );
}

function Interpretation({ rows }: { rows: BenchmarkRow[] }) {
  const m = buildMatrix(rows);
  if (!m.hasAny) return null;
  const tone = {
    hybrid: "border-mode-hybrid/40 text-mode-hybrid",
    graph: "border-mode-graph/40 text-mode-graph",
    tie: "border-warning/40 text-warning",
  }[m.verdict.tone];
  return (
    <div>
      <SectionTitle>Comparison summary</SectionTitle>
      <div className={cn("mb-4 rounded-lg border-l-2 bg-card px-4 py-3 text-sm font-medium", tone)}>{m.verdict.text}</div>
      {m.rows.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead>GraphRAG</TableHead>
                <TableHead>Hybrid GraphRAG</TableHead>
                <TableHead>Leading approach</TableHead>
                <TableHead>Margin</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {m.rows.map((r) => (
                <TableRow key={r.label}>
                  <TableCell className="font-medium">{r.label}</TableCell>
                  <TableCell className="font-mono text-xs">{fmtMetric(r.graph, r.unit)}</TableCell>
                  <TableCell className="font-mono text-xs">{fmtMetric(r.hybrid, r.unit)}</TableCell>
                  <TableCell
                    className={cn(
                      "text-xs font-medium",
                      r.winner === "hybrid" && "text-mode-hybrid",
                      r.winner === "graph" && "text-mode-graph",
                      r.winner === "tie" && "text-muted-foreground",
                    )}
                  >
                    {r.winner === "tie" ? "Tied" : r.winner === "hybrid" ? "Hybrid" : "GraphRAG"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{r.takeaway}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function Fold({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-xl border border-border bg-card">
      <CollapsibleTrigger className="flex w-full items-center justify-between px-5 py-4 text-sm font-medium">
        {title}
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-border p-5">{children}</CollapsibleContent>
    </Collapsible>
  );
}

function DeepDive({ rows }: { rows: BenchmarkRow[] }) {
  const qids = useMemo(() => Array.from(new Set(rows.map((r) => r.question_id))), [rows]);
  const [qid, setQid] = useState<string | null>(qids[0] ?? null);
  const current = (qid && qids.includes(qid) ? qid : qids[0]) ?? null;
  if (!current) return null;
  const qRows = rows.filter((r) => r.question_id === current);
  const first = qRows[0];
  if (!first) return null;
  const expFiles = asList(first.expected_files);
  const modesInQ = Array.from(new Set(qRows.map((r) => r.mode)));

  const fmtQ = (q: string) => {
    const r = rows.find((x) => x.question_id === q);
    return `[${q}] ${(r?.question || q).slice(0, 75)}`;
  };

  return (
    <Fold title="Query & retrieval check vs. ground truth">
      <SearchSelect value={current} options={qids} onChange={setQid} format={fmtQ} searchPlaceholder="Select query…" />

      {/* Concise Query & Expected Targets Bar */}
      <div className="mt-4 rounded-lg border border-mode-ast/25 bg-mode-ast/5 px-4 py-3">
        <div className="text-sm font-medium text-foreground">“{first.question || current}”</div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-muted-foreground">Expected files:</span>
          {expFiles.length ? expFiles.map((f) => <Chip key={f} label={f} mono />) : <span className="text-muted-foreground">None</span>}
        </div>
      </div>

      {/* Compact Side-by-Side Comparison */}
      <div className={cn("mt-3 grid gap-3", modesInQ.length > 1 && "md:grid-cols-2")}>
        {modesInQ.map((m) => {
          const r = qRows.find((x) => x.mode === m)!;
          const hybrid = m.includes("HYBRID");
          const files = asList(r.retrieved_files).slice(0, 4);
          return (
            <div key={m} className="rounded-lg border border-border bg-surface p-3.5 text-xs">
              <div className="flex items-center justify-between gap-2">
                <ModeBadge mode={hybrid ? "hybrid" : "graph"} />
                <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                  <span>Recall: <b className="text-foreground">{isNum(r.recall_at_k) ? `${Math.round(r.recall_at_k * 100)}%` : "N/A"}</b></span>
                  <span>·</span>
                  <span>F1: <b className="text-foreground">{isNum(r.impact_f1) ? `${Math.round(r.impact_f1 * 100)}%` : "N/A"}</b></span>
                  <span>·</span>
                  <span>{isNum(r.total_latency_s) ? `${r.total_latency_s.toFixed(2)}s` : "—"}</span>
                </div>
              </div>
              <div className="mt-2.5 flex flex-wrap gap-1">
                {files.length ? (
                  files.map((f) => <Chip key={f} hit={expFiles.includes(f)} mono label={f} />)
                ) : (
                  <span className="text-muted-foreground">No files retrieved</span>
                )}
              </div>
              {r.generated_answer && (
                <p className="mt-2.5 line-clamp-3 border-t border-border pt-2 leading-relaxed text-muted-foreground">
                  {r.generated_answer}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </Fold>
  );
}

function DetailedResults({ rows }: { rows: BenchmarkRow[] }) {
  const [cat, setCat] = useState("All");
  const [mode, setMode] = useState("All");
  const cats = ["All", ...Array.from(new Set(rows.map((r) => r.category).filter(Boolean))).sort()];
  const modes = ["All", ...Array.from(new Set(rows.map((r) => r.mode).filter(Boolean))).sort()];
  const filtered = rows.filter((r) => (cat === "All" || r.category === cat) && (mode === "All" || r.mode === mode));
  return (
    <Fold title="Detailed per-question results & CSV export">
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <Field label="Filter category">
          <Select value={cat} onValueChange={setCat}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {cats.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Filter mode">
          <Select value={mode} onValueChange={setMode}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {modes.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
      <div className="max-h-[300px] overflow-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              {["QID", "Category", "Mode", "Recall@K", "Precision@K", "Impact F1", "Correctness", "Faithfulness", "Latency", "Status"].map((h) => (
                <TableHead key={h} className="whitespace-nowrap">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((r, i) => (
              <TableRow key={`${r.question_id}-${r.mode}-${i}`} className="font-mono text-xs">
                <TableCell className="whitespace-nowrap">{r.question_id}</TableCell>
                <TableCell className="whitespace-nowrap font-sans">{r.category}</TableCell>
                <TableCell>{r.mode}</TableCell>
                {(["recall_at_k", "precision_at_k", "impact_f1", "correctness", "faithfulness"] as const).map((k) => (
                  <TableCell key={k}>{fmtMetric(r[k], "%")}</TableCell>
                ))}
                <TableCell>{fmtMetric(r.total_latency_s, "s")}</TableCell>
                <TableCell>{r.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button variant="secondary" className="mt-4 w-full" onClick={() => downloadText("repomind_benchmark_results.csv", rowsToCsv(rows), "text/csv")}>
        <Download className="h-4 w-4" /> Download full benchmark CSV
      </Button>
    </Fold>
  );
}

function Chip({ label, hit, mono }: { label: string; hit?: boolean; mono?: boolean }) {
  return (
    <span
      className={cn(
        "rounded border px-1.5 py-0.5 text-[11px]",
        mono && "font-mono",
        hit ? "border-success/30 bg-success/10 text-success" : "border-border bg-muted/60 text-muted-foreground",
      )}
    >
      {hit && "✓ "}
      {label}
    </span>
  );
}

function Glossary() {
  return (
    <Fold title="Metric glossary">
      <Markdown>
        {`| Metric | Meaning | Formula |
|---|---|---|
| **Recall@K** | Fraction of expected files retrieved | True Positives / Expected Files |
| **Precision@K** | Fraction of retrieved files that were relevant | True Positives / K Retrieved |
| **Impact F1** | Accuracy predicting affected components | 2 · P · R / (P + R) |
| **Correctness** | Token overlap with reference answer | Token F1 vs reference |
| **Faithfulness** | Grounding in retrieved code context | Grounded tokens / Answer tokens |
| **Latency** | End-to-end retrieval + generation time | Seconds |`}
      </Markdown>
    </Fold>
  );
}
