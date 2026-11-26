import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ChevronDown, Download, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LatencyChart, ScoreChart } from "@/components/app/BenchmarkCharts";
import { CodeBlock } from "@/components/app/CodeBlock";
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
  const { summary, client, connection, benchmark, setBenchmark } = useWorkspace();
  const [gt, setGt] = useState<GtSource>("ast");
  const [speed, setSpeed] = useState<SpeedMode>("fast");
  const [modeIdx, setModeIdx] = useState(0);
  const [numQ, setNumQ] = useState(3);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ message: string; progress: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const modes = MODE_CHOICES[modeIdx].modes;
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

  return (
    <>
      <PageHeader
        eyebrow="Evaluation & Benchmark"
        title="How well does each retrieval mode understand this repo?"
        description={
          <span className="inline-flex flex-wrap items-center gap-1.5">
            Compare <ModeBadge mode="graph" /> vs <ModeBadge mode="hybrid" /> against <ModeBadge mode="ast" />
          </span>
        }
      />

      <div className="mb-5 grid gap-3 md:grid-cols-3">
        <Pill label="Active repository" value={summary?.meta?.full_name ?? "Loaded Repo"} />
        <Pill label="Code graph nodes" value={`${(summary?.nodes ?? 0).toLocaleString()} AST nodes`} />
        <Pill label="Last run time" value={benchmark.lastRun ? benchmark.lastRun.toTimeString().slice(0, 8) : "Not run yet"} />
      </div>

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
          <Field
            label="Execution engine"
            hint={connection.mode === "demo" ? "Sample results were recorded with the local engine." : undefined}
          >
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
          <div className="mt-5 space-y-2">
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
        <div className="mt-10 space-y-10">
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
            <DetailedResults rows={rows} />
            <DeepDive rows={rows} />
          </div>
        </div>
      )}
      <div className="mt-3">
        <Glossary />
      </div>
    </>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <div className="text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-sm">{value}</div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs text-muted-foreground">{label}</div>
      {children}
      {hint && <div className="mt-1 text-[11px] text-muted-foreground/80">{hint}</div>}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-4 text-sm font-semibold tracking-tight">{children}</h2>;
}

function EmptyState() {
  return (
    <div className="mt-10 rounded-xl border border-dashed border-border px-6 py-12 text-center">
      <h3 className="text-base font-semibold">Ready for ground-truth evaluation</h3>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">
        Select your parameters above and click <span className="text-foreground">Run benchmark</span> to evaluate GraphRAG vs Hybrid GraphRAG against
        mathematically verified repository facts.
      </p>
      <div className="mx-auto mt-8 grid max-w-3xl gap-4 text-left md:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h4 className="text-sm font-medium text-mode-ast">Live AST ground truth</h4>
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            Synthesizes benchmark test suites directly from the repository's syntax tree. Target files, callers, and test suites are 100%
            deterministic with zero LLM hallucination.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <h4 className="text-sm font-medium text-mode-hybrid">Works on any repository</h4>
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            No manual test annotations required. RepoMind scans topological hubs in any ingested GitHub repo and automatically generates an
            explainable What-If benchmark suite on the fly.
          </p>
        </div>
      </div>
    </div>
  );
}

const KPIS = [
  { title: "Retrieval recall", metric: "recall_at_k", unit: "%" as const, desc: "% of relevant files successfully retrieved", hib: true },
  { title: "Impact detection", metric: "impact_f1", unit: "%" as const, desc: "F1 score for detecting blast-radius affected components", hib: true },
  { title: "Answer faithfulness", metric: "faithfulness", unit: "%" as const, desc: "% of generated answer grounded in retrieved code", hib: true },
  { title: "Response speed", metric: "total_latency_s", unit: "s" as const, desc: "Total end-to-end execution time", hib: false },
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
              <div className="mt-4 space-y-2">
                <KpiRow label="Graph" tone="graph" v={fmtMetric(gv, k.unit)} />
                <KpiRow label="Hybrid" tone="hybrid" v={fmtMetric(hv, k.unit)} />
              </div>
              <div className="mt-4 border-t border-border pt-3 text-[11px] text-muted-foreground">{k.desc}</div>
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
  if (!m.hasAny) return <p className="text-sm text-muted-foreground">Run benchmark to view comparison insights.</p>;
  const tone = {
    hybrid: "border-mode-hybrid/40 text-mode-hybrid",
    graph: "border-mode-graph/40 text-mode-graph",
    tie: "border-warning/40 text-warning",
  }[m.verdict.tone];
  return (
    <div>
      <SectionTitle>Key takeaways & comparison matrix</SectionTitle>
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
                <TableHead>Summary</TableHead>
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

function DetailedResults({ rows }: { rows: BenchmarkRow[] }) {
  const [cat, setCat] = useState("All");
  const [mode, setMode] = useState("All");
  const cats = ["All", ...Array.from(new Set(rows.map((r) => r.category).filter(Boolean))).sort()];
  const modes = ["All", ...Array.from(new Set(rows.map((r) => r.mode).filter(Boolean))).sort()];
  const filtered = rows.filter((r) => (cat === "All" || r.category === cat) && (mode === "All" || r.mode === mode));
  return (
    <Fold title="Detailed results table & CSV export">
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
      <div className="max-h-[320px] overflow-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              {["QID", "Category", "Mode", "Recall@K", "Precision@K", "Impact F1", "Correctness", "Faithfulness", "Total Latency", "Status"].map((h) => (
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

function DeepDive({ rows }: { rows: BenchmarkRow[] }) {
  const qids = useMemo(() => Array.from(new Set(rows.map((r) => r.question_id))), [rows]);
  const [qid, setQid] = useState<string | null>(qids[0] ?? null);
  const current = qid && qids.includes(qid) ? qid : qids[0];
  const qRows = rows.filter((r) => r.question_id === current);
  if (!qRows.length) return null;
  const first = qRows[0];
  const expFiles = asList(first.expected_files);
  const expComps = asList(first.expected_components);
  const modesInQ = Array.from(new Set(qRows.map((r) => r.mode)));
  const fmtQ = (q: string) => {
    const r = rows.find((x) => x.question_id === q);
    return `[${q}] ${(r?.question || q).slice(0, 70)}...`;
  };

  return (
    <Fold title="Query & retrieval deep dive vs. ground truth">
      <SearchSelect value={current} options={qids} onChange={setQid} format={fmtQ} searchPlaceholder="Search questions…" />

      <div className="mt-5 rounded-xl border border-mode-ast/25 bg-mode-ast/5 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-mode-ast">Verified ground truth · {first.category || "General"}</span>
          <span className="rounded-full border border-mode-ast/30 bg-mode-ast/10 px-2 py-0.5 text-[11px] text-mode-ast">Compiler AST truth</span>
        </div>
        <h4 className="mt-2 font-medium">Query: “{first.question || current}”</h4>
        <div className="mt-3 space-y-2 text-sm">
          <ChipRow label="Target files" items={expFiles} mono />
          <ChipRow label="Blast radius components" items={expComps} />
        </div>
        <div className="mt-3 rounded-lg border border-border bg-card/60 p-3 text-sm">
          <span className="font-medium">Reference answer: </span>
          <span className="text-muted-foreground">{first.reference_answer || "—"}</span>
        </div>
      </div>

      <div className={cn("mt-4 grid gap-4", modesInQ.length > 1 && "md:grid-cols-2")}>
        {modesInQ.map((m) => {
          const r = qRows.find((x) => x.mode === m)!;
          const hybrid = m.includes("HYBRID");
          const files = asList(r.retrieved_files).slice(0, 4);
          const comps = asList(r.retrieved_components).slice(0, 4);
          return (
            <div key={m} className={cn("rounded-xl border border-border bg-card p-4", hybrid ? "border-t-mode-hybrid" : "border-t-mode-graph", "border-t-2")}>
              <div className="flex items-center justify-between">
                <ModeBadge mode={hybrid ? "hybrid" : "graph"} />
                <span className="font-mono text-xs text-muted-foreground">{isNum(r.total_latency_s) ? `${r.total_latency_s.toFixed(2)}s` : "—"}</span>
              </div>
              <div className="mt-3 flex gap-2 text-xs">
                <span className="rounded bg-muted px-2 py-0.5">
                  Recall: <b className="font-mono">{isNum(r.recall_at_k) ? `${Math.round(r.recall_at_k * 100)}%` : "N/A"}</b>
                </span>
                <span className="rounded bg-muted px-2 py-0.5">
                  Impact F1: <b className="font-mono">{isNum(r.impact_f1) ? `${Math.round(r.impact_f1 * 100)}%` : "N/A"}</b>
                </span>
              </div>
              <div className="mt-3 text-xs text-muted-foreground">Retrieved files</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {files.length ? (
                  files.map((f) => <Chip key={f} hit={expFiles.includes(f)} mono label={f} />)
                ) : (
                  <span className="text-xs text-muted-foreground">No files retrieved</span>
                )}
              </div>
              <div className="mt-3 text-xs text-muted-foreground">Detected components</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {comps.length ? (
                  comps.map((c, i) => <Chip key={`${c}-${i}`} hit={expComps.includes(c)} label={c} />)
                ) : (
                  <span className="text-xs text-muted-foreground">None detected</span>
                )}
              </div>
              <div className="mt-4 rounded-lg border border-border bg-surface p-3">
                <div className={cn("mb-1 text-xs font-medium", hybrid ? "text-mode-hybrid" : "text-mode-graph")}>Generated answer</div>
                <Markdown className="text-[13px]">{r.generated_answer || "—"}</Markdown>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <Fold title="Inspect exact prompt context sent to LLM">
          <Tabs defaultValue={modesInQ[0]}>
            <TabsList>
              {modesInQ.map((m) => (
                <TabsTrigger key={m} value={m}>
                  {m} context
                </TabsTrigger>
              ))}
            </TabsList>
            {modesInQ.map((m) => {
              const ctx = qRows.find((x) => x.mode === m)?.prompt_context;
              return (
                <TabsContent key={m} value={m} className="mt-3">
                  {ctx ? <CodeBlock code={ctx} maxHeight={380} /> : <p className="text-xs text-muted-foreground">No prompt context recorded.</p>}
                </TabsContent>
              );
            })}
          </Tabs>
        </Fold>
      </div>
    </Fold>
  );
}

function ChipRow({ label, items, mono }: { label: string; items: string[]; mono?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-xs font-medium">{label}:</span>
      {items.length ? items.map((i) => <Chip key={i} label={i} mono={mono} />) : <span className="text-xs text-muted-foreground">None</span>}
    </div>
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
    <Fold title="Metric glossary & evaluation methodology">
      <Markdown>
        {`| Metric | Plain English | Formula |
|---|---|---|
| **Recall@K** | Did the system find all relevant files? | True Positives / Expected Files |
| **Precision@K** | Were the retrieved files actually relevant? | True Positives / K Retrieved |
| **Impact F1** | Accuracy in predicting affected blast radius | 2 · Precision · Recall / (P + R) |
| **Answer Correctness** | Semantic token overlap with golden answer | Token-level F1 vs reference |
| **Answer Faithfulness** | Was the answer grounded in retrieved code? | Grounded tokens / Answer tokens |
| **Total Latency** | End-to-end execution time (Retrieval + LLM) | Seconds |

**Why Live AST Ground Truth Matters:**
Conventional RAG benchmarks rely on LLM-generated questions and answers, introducing circular evaluation bias.
RepoMind extracts actual callers, test suites, and imports from the **Python Abstract Syntax Tree (AST)**,
guaranteeing 100% objective, mathematically verifiable benchmark facts with zero hallucination.`}
      </Markdown>
    </Fold>
  );
}
