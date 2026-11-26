import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CodeBlock } from "@/components/app/CodeBlock";
import { Mono, PageHeader, RequireRepo, Section } from "@/components/app/Page";
import { SearchSelect } from "@/components/app/SearchSelect";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { RelationLegend } from "@/components/graph/GraphLegend";
import { filterGraph, NODE_COLORS, PHYSICS_LABELS, type PhysicsPreset } from "@/lib/repomind/graph-style";
import { useFileQuery, useFilesQuery, useGraphQuery } from "@/lib/repomind/queries";
import type { GraphNode } from "@/lib/repomind/types";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/explorer")({
  head: () => ({
    meta: [
      { title: "Repository Explorer — RepoMind" },
      { name: "description", content: "Explore an interactive knowledge graph of components, calls, imports and dependencies." },
      { property: "og:title", content: "Repository Explorer — RepoMind" },
      { property: "og:description", content: "Explore an interactive knowledge graph of components, calls, imports and dependencies." },
    ],
  }),
  component: () => (
    <RequireRepo>
      <Explorer />
    </RequireRepo>
  ),
});

function Explorer() {
  const { summary } = useWorkspace();
  return (
    <>
      <PageHeader
        eyebrow="Repository Explorer"
        title={<span className="font-mono">{summary?.meta?.full_name}</span>}
        description="Explore interactive component call-graphs, architectural hubs, dependencies, and source files."
      />
      <Tabs defaultValue="graph">
        <TabsList className="mb-6">
          <TabsTrigger value="graph">Architecture graph</TabsTrigger>
          <TabsTrigger value="codebase">Codebase & architecture overview</TabsTrigger>
        </TabsList>
        <TabsContent value="graph">
          <GraphTab />
        </TabsContent>
        <TabsContent value="codebase">
          <CodebaseTab />
        </TabsContent>
      </Tabs>
    </>
  );
}

function GraphTab() {
  const { data, isLoading, error } = useGraphQuery();
  const available = useMemo(() => Object.keys(data?.stats.node_type_breakdown ?? {}), [data]);
  const [types, setTypes] = useState<string[] | null>(null);
  const [preset, setPreset] = useState<PhysicsPreset>("jiggly");
  const [spacing, setSpacing] = useState(120);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Default: first six entity types, like the original filter.
  useEffect(() => {
    if (data && types === null) setTypes(available.length >= 6 ? available.slice(0, 6) : available);
  }, [data, available, types]);

  const sortedIds = useMemo(() => (data ? data.nodes.map((n) => n.id).sort() : []), [data]);
  const byId = useMemo(() => new Map((data?.nodes ?? []).map((n) => [n.id, n])), [data]);
  useEffect(() => {
    if (sortedIds.length && (!selectedId || !byId.has(selectedId))) setSelectedId(sortedIds[0]);
  }, [sortedIds, byId, selectedId]);

  const filtered = useMemo(
    () => (data ? filterGraph(data.nodes, data.edges, types ?? [], {}) : { nodes: [], edges: [] }),
    [data, types],
  );
  const relations = useMemo(() => Array.from(new Set(filtered.edges.map((e) => e.relation))), [filtered.edges]);

  if (isLoading || !data)
    return error ? (
      <p className="text-sm text-danger">{(error as Error).message}</p>
    ) : (
      <div className="flex h-[580px] items-center justify-center rounded-xl border border-border text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading graph…
      </div>
    );

  const toggle = (t: string) =>
    setTypes((prev) => {
      const cur = prev ?? [];
      return cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t];
    });

  const formatNode = (id: string) => {
    const n = byId.get(id);
    if (!n) return id;
    return n.file_path ? `${n.name} [${n.type}] — ${n.file_path}` : `${n.name} [${n.type}]`;
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-5 rounded-xl border border-border bg-card p-5 lg:grid-cols-[1.6fr_1fr_0.9fr]">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Visible entity types</span>
            <span className="flex gap-2 text-[11px]">
              <button className="text-muted-foreground hover:text-foreground" onClick={() => setTypes(available)}>
                All
              </button>
              <span className="text-border">|</span>
              <button className="text-muted-foreground hover:text-foreground" onClick={() => setTypes([])}>
                Clear
              </button>
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {available.map((t) => {
              const on = (types ?? []).includes(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => toggle(t)}
                  aria-pressed={on}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-all",
                    on ? "border-foreground/20 bg-accent text-foreground" : "border-border text-muted-foreground/70 hover:text-foreground",
                  )}
                >
                  <span
                    className="h-2 w-2 rounded-full transition-opacity"
                    style={{ background: NODE_COLORS[t] ?? NODE_COLORS.Unknown, opacity: on ? 1 : 0.3 }}
                  />
                  {t}
                  <span className="font-mono text-[10px] text-muted-foreground">{data.stats.node_type_breakdown[t]}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <span className="mb-2 block text-xs font-medium text-muted-foreground">Movement dynamics</span>
          <div className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-surface p-1">
            {PHYSICS_LABELS.map((p) => (
              <button
                key={p.value}
                type="button"
                title={p.hint}
                onClick={() => setPreset(p.value)}
                className={cn(
                  "rounded-md px-2 py-1.5 text-[11.5px] leading-tight transition-colors",
                  preset === p.value ? "bg-accent text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between text-xs">
            <span className="font-medium text-muted-foreground">Spring spacing</span>
            <span className="font-mono text-foreground">{spacing}</span>
          </div>
          <Slider min={70} max={220} step={10} value={[spacing]} onValueChange={([v]) => setSpacing(v)} />
        </div>
      </div>

      <KnowledgeGraph
        nodes={filtered.nodes}
        edges={filtered.edges}
        preset={preset}
        springLength={spacing}
        height={580}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />
      <RelationLegend relations={relations} />

      <Section title="Inspect entity details" description="Pick an entity, or click any node in the graph.">
        <SearchSelect
          value={selectedId}
          options={sortedIds}
          onChange={setSelectedId}
          format={formatNode}
          searchPlaceholder="Search entities…"
        />
        {selectedId && byId.get(selectedId) && <NodeDetails node={byId.get(selectedId)!} />}
      </Section>
    </div>
  );
}

function NodeDetails({ node }: { node: GraphNode }) {
  return (
    <div className="mt-5 grid gap-6 md:grid-cols-[1fr_1.8fr]">
      <dl className="space-y-3 text-sm">
        <Row k="Entity name">
          <Mono>{node.name}</Mono>
        </Row>
        <Row k="Type">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: NODE_COLORS[node.type] ?? NODE_COLORS.Unknown }} />
            {node.type}
          </span>
        </Row>
        <Row k="File location">
          <Mono>{node.file_path || "Repository-level"}</Mono>
          <span className="ml-1.5 text-xs text-muted-foreground">line {node.line_number || 1}</span>
        </Row>
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="rounded-lg border border-border p-3">
            <div className="font-mono text-2xl">{node.in_degree ?? 0}</div>
            <div className="text-[11px] text-muted-foreground">In-degree · incoming callers</div>
          </div>
          <div className="rounded-lg border border-border p-3">
            <div className="font-mono text-2xl">{node.out_degree ?? 0}</div>
            <div className="text-[11px] text-muted-foreground">Out-degree · outgoing deps</div>
          </div>
        </div>
      </dl>
      <div className="min-w-0 space-y-4">
        {node.docstring && (
          <div>
            <div className="mb-1.5 text-xs font-medium text-muted-foreground">Docstring / description</div>
            <p className="rounded-lg border border-signal/20 bg-signal/5 px-3.5 py-2.5 text-sm leading-relaxed">{node.docstring}</p>
          </div>
        )}
        {node.source_snippet && (
          <div>
            <div className="mb-1.5 text-xs font-medium text-muted-foreground">Source code snippet</div>
            <CodeBlock code={node.source_snippet} maxHeight={340} />
          </div>
        )}
        {!node.docstring && !node.source_snippet && (
          <p className="text-sm text-muted-foreground">No docstring or source snippet recorded for this entity.</p>
        )}
      </div>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{k}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}

function CodebaseTab() {
  const { data } = useGraphQuery();
  const files = useFilesQuery();
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    if (files.data?.length && !path) setPath(files.data[0].path);
  }, [files.data, path]);
  const file = useFileQuery(path);
  const hubs = data?.stats.top_hubs ?? [];
  const libs = data?.libraries ?? [];

  const lang = file.data?.extension;

  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Top architectural hubs" description="Most connected classes and functions across the repository.">
          {hubs.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Component</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Callers (in)</TableHead>
                  <TableHead className="text-right">Calls (out)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hubs.map((h) => (
                  <TableRow key={h.id}>
                    <TableCell className="font-mono text-xs">{h.name}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5 text-xs">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: NODE_COLORS[h.type] ?? NODE_COLORS.Unknown }} />
                        {h.type}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">{h.in_degree}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{h.out_degree}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No architectural hubs detected.</p>
          )}
        </Section>
        <Section title="Detected third-party packages" description="Libraries extracted from requirements and project manifests.">
          {libs.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Package</TableHead>
                  <TableHead>Specifier</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {libs.map((l, i) => (
                  <TableRow key={`${l.name}-${i}`}>
                    <TableCell className="font-mono text-xs">{l.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{l.specifier}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{l.source}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No external dependencies detected.</p>
          )}
        </Section>
      </div>

      <Section title="Source code & documentation browser">
        {files.data?.length ? (
          <div className="space-y-4">
            <SearchSelect value={path} options={files.data.map((f) => f.path)} onChange={setPath} searchPlaceholder="Search files…" />
            {file.data && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    ["File type", file.data.file_type.toUpperCase()],
                    ["Size", `${file.data.size_bytes.toLocaleString()} bytes`],
                    ["Line count", file.data.line_count],
                  ].map(([k, v]) => (
                    <div key={k as string} className="rounded-lg border border-border p-3">
                      <div className="text-[11px] text-muted-foreground">{k}</div>
                      <div className="mt-0.5 font-mono text-lg">{v}</div>
                    </div>
                  ))}
                </div>
                <CodeBlock code={file.data.content} lineNumbers className={lang === ".md" ? "" : ""} maxHeight={600} />
              </>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No files available.</p>
        )}
      </Section>
    </div>
  );
}
