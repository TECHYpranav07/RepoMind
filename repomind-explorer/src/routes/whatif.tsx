import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Download,
  FileJson,
  FileText,
  FlaskConical,
  GitBranch,
  Layers,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Markdown } from "@/components/app/Markdown";
import { Mono, PageHeader, RequireRepo, Section } from "@/components/app/Page";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { ImpactLegend } from "@/components/graph/GraphLegend";
import { downloadText } from "@/lib/repomind/download";
import { useScenariosQuery } from "@/lib/repomind/queries";
import type { ImpactEntity, WhatIfResult } from "@/lib/repomind/types";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/whatif")({
  head: () => ({
    meta: [
      { title: "What-If Analysis — RepoMind" },
      { name: "description", content: "Simulate refactors, replacements and removals and see their explainable change impact." },
      { property: "og:title", content: "What-If Analysis — RepoMind" },
      { property: "og:description", content: "Simulate refactors, replacements and removals and see their explainable change impact." },
    ],
  }),
  component: () => (
    <RequireRepo>
      <WhatIf />
    </RequireRepo>
  ),
});

function WhatIf() {
  const { summary, client, whatifResult, setWhatifResult, whatifInput, setWhatifInput } = useWorkspace();
  const scenarios = useScenariosQuery();
  const [depth, setDepth] = useState(2);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!whatifInput.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      setWhatifResult(await client.whatif(whatifInput.trim(), depth));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="What-If Analysis"
        title="Explainable change-impact analysis"
        description={
          <>
            Simulate hypothetical refactorings, component replacements, removals, or upgrades on{" "}
            <span className="font-mono text-foreground">{summary?.meta?.full_name}</span> using evidence-grounded dependency graph traversal.
          </>
        }
      />

      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-2 text-xs font-medium text-muted-foreground">Quick scenarios</div>
        <div className="mb-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {scenarios.data?.map((s) => (
            <button
              key={s.query}
              type="button"
              onClick={() => setWhatifInput(s.query)}
              className={cn(
                "rounded-lg border px-3 py-2.5 text-left text-[13px] transition-colors",
                whatifInput === s.query ? "border-signal/50 bg-signal/10" : "border-border hover:bg-accent/50",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run();
          }}
          className="grid gap-4 lg:grid-cols-[1fr_auto]"
        >
          <div>
            <label htmlFor="hyp" className="mb-1.5 block text-xs text-muted-foreground">
              Enter a hypothetical software modification
            </label>
            <Input
              id="hyp"
              value={whatifInput}
              onChange={(e) => setWhatifInput(e.target.value)}
              placeholder="e.g. What if we replace FAISS with ChromaDB? or What if we remove Redis caching?"
              className="h-11"
            />
          </div>
          <div className="flex items-end gap-4">
            <div className="w-56">
              <div className="mb-3 flex justify-between text-xs">
                <span className="text-muted-foreground">Upstream / downstream depth</span>
                <span className="font-mono">{depth}</span>
              </div>
              <Slider min={1} max={4} step={1} value={[depth]} onValueChange={([v]) => setDepth(v)} />
            </div>
            <Button type="submit" className="h-11 px-5" disabled={busy || !whatifInput.trim()}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Analyze impact
            </Button>
          </div>
        </form>
        {busy && (
          <p className="mt-4 text-xs text-muted-foreground">
            Analyzing dependency graph neighborhood and generating explainable impact report…
          </p>
        )}
        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2.5 text-sm text-warning">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
          </div>
        )}
      </div>

      {whatifResult && <Results res={whatifResult} />}
    </>
  );
}

const RISK = {
  High: "text-danger border-danger/40 bg-danger/10",
  Medium: "text-warning border-warning/40 bg-warning/10",
  Low: "text-success border-success/40 bg-success/10",
} as Record<string, string>;
const RISK_BAR = { High: "bg-danger", Medium: "bg-warning", Low: "bg-success" } as Record<string, string>;

function Results({ res }: { res: WhatIfResult }) {
  const risk = res.risk_level || "Medium";
  const action = (res.action || "MODIFY").toUpperCase();
  const target = res.target_entity || "N/A";
  const impact = useMemo(
    () => ({
      target: new Set(res.target_nodes.map((t) => t.id)),
      direct: new Set(res.direct_affected.map((t) => t.id)),
      inferred: new Set(res.inferred_affected.map((t) => t.id)),
    }),
    [res],
  );

  return (
    <div className="mt-8 space-y-5">
      <div className="relative overflow-hidden rounded-xl border border-border bg-card px-6 py-5">
        <span className={cn("absolute inset-y-0 left-0 w-1", RISK_BAR[risk] ?? RISK_BAR.Medium)} />
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Proposed modification</div>
            <h2 className="mt-1 text-lg font-semibold">
              {action} <Mono>{target}</Mono>
              {res.replacement_entity && (
                <>
                  {" "}
                  with <Mono>{res.replacement_entity}</Mono>
                </>
              )}
            </h2>
          </div>
          <span className={cn("self-start rounded-full border px-3.5 py-1 text-xs font-semibold tracking-wide md:self-center", RISK[risk] ?? RISK.Medium)}>
            {risk.toUpperCase()} RISK
          </span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 border-t border-border pt-4 text-sm sm:max-w-lg">
          <Stat n={res.direct_affected.length} l="direct callers" />
          <Stat n={res.inferred_affected.length} l="transitive components" />
          <Stat n={res.tests_to_update.length} l="relevant test suites" />
        </div>
      </div>

      <Tabs defaultValue="report">
        <TabsList className="flex h-auto flex-wrap justify-start">
          <TabsTrigger value="report">Impact report</TabsTrigger>
          <TabsTrigger value="subgraph">Impacted subgraph</TabsTrigger>
          <TabsTrigger value="inventory">Affected components</TabsTrigger>
          <TabsTrigger value="paths">Reasoning paths</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>

        <TabsContent value="report" className="mt-5">
          <ImpactReportView markdown={res.report_markdown || ""} />
        </TabsContent>

        <TabsContent value="subgraph" className="mt-5 space-y-4">
          <ImpactLegend />
          {res.impact_subgraph.nodes.length > 0 ? (
            <KnowledgeGraph
              nodes={res.impact_subgraph.nodes}
              edges={res.impact_subgraph.edges}
              impact={impact}
              preset="jiggly"
              springLength={130}
              height={560}
            />
          ) : (
            <p className="text-sm text-muted-foreground">No connected subgraph nodes found for this entity.</p>
          )}
        </TabsContent>

        <TabsContent value="inventory" className="mt-5">
          <div className="grid gap-5 md:grid-cols-2">
            <EntityList title="Directly impacted (1-hop)" items={res.direct_affected} empty="None detected." showType />
            <EntityList title="Inferred / transitive (>1-hop)" items={res.inferred_affected} empty="None detected." showType />
            <EntityList title="Tests requiring updates" items={res.tests_to_update} empty="No direct tests found covering this component." />
            <EntityList title="Configuration files" items={res.configs_to_update} empty="No configuration files explicitly linked." noLine />
          </div>
        </TabsContent>

        <TabsContent value="paths" className="mt-5 space-y-5">
          <Section title="Computed dependency reasoning paths" description="The causal chain connecting each affected component to the proposed change.">
            {res.impact_paths.length ? (
              <ul className="space-y-2">
                {res.impact_paths.map((p, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    <span
                      className={cn(
                        "mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10.5px] font-medium",
                        p.is_direct ? "border-danger/40 bg-danger/10 text-danger" : "border-warning/40 bg-warning/10 text-warning",
                      )}
                    >
                      {p.is_direct ? "Direct" : `Depth ${p.depth}`}
                    </span>
                    <span className="font-mono text-[12.5px] text-foreground/85">{p.path_text}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No relationship paths discovered.</p>
            )}
          </Section>
          <Section title="Supporting source citations">
            {res.citations.length ? (
              <ul className="space-y-3">
                {res.citations.map((c) => (
                  <li key={c.id} className="text-sm">
                    <span className="font-medium">[Source {c.id}]</span>{" "}
                    <code className="font-mono text-xs text-foreground/80">
                      {c.file_path}:{c.start_line}-{c.end_line}
                    </code>
                    <p className="mt-1 border-l-2 border-border pl-2.5 text-xs italic text-muted-foreground">{c.snippet}...</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No citations retrieved.</p>
            )}
          </Section>
        </TabsContent>

        <TabsContent value="export" className="mt-5">
          <Section title="Export what-if impact report">
            <div className="grid gap-3 sm:grid-cols-2">
              <Button
                variant="secondary"
                className="h-12"
                onClick={() => downloadText(`repomind_whatif_${res.action}_${res.target_entity}.md`, res.export_markdown, "text/markdown")}
              >
                <FileText className="h-4 w-4" /> Download as Markdown (.md) <Download className="ml-auto h-3.5 w-3.5 opacity-60" />
              </Button>
              <Button
                variant="secondary"
                className="h-12"
                onClick={() =>
                  downloadText(
                    `repomind_whatif_${res.action}_${res.target_entity}.json`,
                    JSON.stringify(res.export_json, null, 2),
                    "application/json",
                  )
                }
              >
                <FileJson className="h-4 w-4" /> Download as JSON (.json) <Download className="ml-auto h-3.5 w-3.5 opacity-60" />
              </Button>
            </div>
          </Section>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ n, l }: { n: number; l: string }) {
  return (
    <div>
      <div className="font-mono text-2xl">{n}</div>
      <div className="text-[11px] text-muted-foreground">{l}</div>
    </div>
  );
}

function EntityList({
  title,
  items,
  empty,
  showType,
  noLine,
}: {
  title: string;
  items: ImpactEntity[];
  empty: string;
  showType?: boolean;
  noLine?: boolean;
}) {
  return (
    <Section title={title} actions={<span className="font-mono text-xs text-muted-foreground">{items.length}</span>}>
      {items.length ? (
        <ul className="divide-y divide-border">
          {items.map((d) => (
            <li key={d.id} className="flex flex-col gap-0.5 py-2 first:pt-0 last:pb-0">
              <span className="text-sm font-medium">
                {d.name}
                {showType && <span className="ml-2 text-xs font-normal text-muted-foreground">{d.type}</span>}
              </span>
              <span className="font-mono text-[11.5px] text-muted-foreground">
                {d.file_path}
                {!noLine && `:${d.line_number || 1}`}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{empty}</p>
      )}
    </Section>
  );
}

interface ReportSection {
  title: string;
  body: string;
}

function formatScannableBody(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  // Break long dense paragraphs into crisp bullet points while preserving existing lists/code blocks.
  const lines = trimmed.split("\n");
  const out: string[] = [];
  let inCode = false;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      inCode = !inCode;
      out.push(line);
      continue;
    }
    const t = line.trim();
    if (!inCode && t.length > 150 && !/^([-*]|\d+\.|>|#|\|)/.test(t)) {
      const sentences = t.split(/(?<=[.!?])\s+(?=[A-Z`*])/).filter(Boolean);
      if (sentences.length > 1) {
        for (const s of sentences) out.push(`- ${s.trim()}`);
        continue;
      }
    }
    out.push(line);
  }
  return out.join("\n");
}

function parseReportSections(markdown: string): ReportSection[] {
  const lines = markdown.split(/\r?\n/);
  const sections: ReportSection[] = [];
  let current: ReportSection | null = null;

  for (const line of lines) {
    const match = line.match(/^#{3,4}\s+(.+)$/);
    if (match && match[1]) {
      if (current && current.body.trim()) sections.push({ ...current, body: formatScannableBody(current.body) });
      const title = match[1].trim();
      // Skip redundant top-level "Proposed Change:" header since the banner above already displays it.
      if (/^Proposed Change:/i.test(title)) {
        current = null;
      } else {
        current = { title, body: "" };
      }
    } else if (current) {
      current.body += (current.body ? "\n" : "") + line;
    }
  }
  if (current && current.body.trim()) sections.push({ ...current, body: formatScannableBody(current.body) });
  return sections;
}

function sectionVisual(title: string) {
  const t = title.toLowerCase();
  if (t.includes("summary")) return { Icon: Sparkles, accent: "border-l-signal text-signal" };
  if (t.includes("risk") || t.includes("hazard")) return { Icon: AlertTriangle, accent: "border-l-danger text-danger" };
  if (t.includes("benefit")) return { Icon: CheckCircle2, accent: "border-l-success text-success" };
  if (t.includes("affected") || t.includes("component")) return { Icon: Layers, accent: "border-l-warning text-warning" };
  if (t.includes("reasoning") || t.includes("path")) return { Icon: GitBranch, accent: "border-l-mode-graph text-mode-graph" };
  if (t.includes("modification")) return { Icon: Wrench, accent: "border-l-signal text-signal" };
  if (t.includes("test")) return { Icon: FlaskConical, accent: "border-l-mode-hybrid text-mode-hybrid" };
  if (t.includes("confidence") || t.includes("evidence")) return { Icon: ShieldCheck, accent: "border-l-muted-foreground text-muted-foreground" };
  return { Icon: FileText, accent: "border-l-border text-foreground" };
}

function ImpactReportView({ markdown }: { markdown: string }) {
  const sections = useMemo(() => parseReportSections(markdown), [markdown]);

  if (!markdown.trim()) {
    return (
      <Section>
        <p className="text-sm text-muted-foreground">No report text generated.</p>
      </Section>
    );
  }

  if (sections.length === 0) {
    return (
      <Section>
        <Markdown>{formatScannableBody(markdown)}</Markdown>
      </Section>
    );
  }

  const lead = sections[0];
  if (!lead) return null;
  const rest = sections.slice(1);
  const isLeadSummary = lead.title.toLowerCase().includes("summary");
  const gridItems = isLeadSummary ? rest : sections;

  return (
    <div className="space-y-4">
      {isLeadSummary && <ReportCard section={lead} />}
      <div className="grid gap-4 md:grid-cols-2">
        {gridItems.map((sec) => (
          <ReportCard key={sec.title} section={sec} />
        ))}
      </div>
    </div>
  );
}

function ReportCard({ section }: { section: ReportSection }) {
  const { Icon, accent } = sectionVisual(section.title);
  const [borderClass, iconColor] = accent.split(" ");
  return (
    <div className={cn("rounded-xl border border-border border-l-2 bg-card p-5", borderClass)}>
      <div className="mb-3 flex items-center gap-2">
        <Icon className={cn("h-4 w-4 shrink-0", iconColor)} />
        <h3 className="text-sm font-semibold tracking-tight text-foreground">{section.title}</h3>
      </div>
      <Markdown className="text-[13.5px] leading-relaxed">{section.body}</Markdown>
    </div>
  );
}
