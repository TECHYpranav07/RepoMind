import { useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ArrowUp, BookOpen, ChevronDown, GitFork, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { Markdown } from "@/components/app/Markdown";
import { PageHeader, RequireRepo } from "@/components/app/Page";
import { useSuggestionsQuery } from "@/lib/repomind/queries";
import type { ChatMessage, ChatMode } from "@/lib/repomind/types";
import { greetingMessage, useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Repository Chat — RepoMind" },
      { name: "description", content: "Ask natural-language questions about a codebase with cited, graph-grounded answers." },
      { property: "og:title", content: "Repository Chat — RepoMind" },
      { property: "og:description", content: "Ask natural-language questions about a codebase with cited, graph-grounded answers." },
    ],
  }),
  component: () => (
    <RequireRepo>
      <Chat />
    </RequireRepo>
  ),
});

let msgSeq = 0;
const nextId = () => `m${Date.now()}-${msgSeq++}`;

function Chat() {
  const { summary, client, chatMessages, setChatMessages } = useWorkspace();
  const fullName = summary?.meta?.full_name ?? "";
  const [mode, setMode] = useState<ChatMode>("hybrid");
  const [topK, setTopK] = useState(4);
  const [depth, setDepth] = useState(2);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const suggestions = useSuggestionsQuery();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatMessages.length === 0) setChatMessages(() => [greetingMessage(fullName, mode)]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatMessages.length, fullName]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chatMessages.length, busy]);

  const ask = async (prompt: string) => {
    const q = prompt.trim();
    if (!q || busy) return;
    setInput("");
    setChatMessages((m) => [...m, { id: nextId(), role: "user", content: q, citations: [], paths: [] }]);
    setBusy(true);
    try {
      const res = await client.chat({ query: q, mode, top_k: topK, graph_depth: depth });
      setChatMessages((m) => [
        ...m,
        {
          id: nextId(),
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          paths: res.graph_paths,
          mode: mode.toUpperCase(),
          model: res.model_used,
          latency: res.latency,
        },
      ]);
    } catch (e) {
      setChatMessages((m) => [
        ...m,
        { id: nextId(), role: "assistant", content: `⚠️ ${(e as Error).message}`, citations: [], paths: [] },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Repository Chat"
        title={<span className="font-mono">{fullName}</span>}
        description="Ask natural-language questions about the codebase architecture, design patterns, and internal wiring."
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_270px]">
        <div className="flex min-h-[640px] flex-col rounded-xl border border-border bg-card">
          <div className="flex-1 space-y-6 overflow-y-auto p-5 md:p-6">
            {chatMessages.map((m) => (
              <Message key={m.id} msg={m} />
            ))}
            {busy && (
              <div className="flex items-center gap-2 pl-10 text-sm text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Retrieving evidence via {mode.toUpperCase()} GraphRAG…
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-4">
            {suggestions.data && (
              <div className="mb-3 flex flex-wrap gap-2">
                {suggestions.data.map((s) => (
                  <button
                    key={s}
                    type="button"
                    disabled={busy}
                    onClick={() => ask(s)}
                    className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-foreground/20 hover:bg-accent hover:text-foreground disabled:opacity-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void ask(input);
              }}
              className="relative"
            >
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void ask(input);
                  }
                }}
                rows={2}
                placeholder="Ask a question about this repository..."
                className="min-h-[56px] resize-none pr-14"
              />
              <Button type="submit" size="icon" disabled={busy || !input.trim()} className="absolute bottom-2.5 right-2.5 h-8 w-8" aria-label="Send">
                <ArrowUp className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-8 lg:self-start">
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-4 text-sm font-semibold">Retrieval settings</h3>
            <div className="mb-1.5 text-xs text-muted-foreground">Retrieval strategy</div>
            <div className="space-y-1.5">
              {(
                [
                  { v: "hybrid", t: "Hybrid (Graph + Vector)", d: "Recommended" },
                  { v: "graph", t: "Graph only", d: "AST traversal" },
                ] as const
              ).map((o) => (
                <button
                  key={o.v}
                  type="button"
                  onClick={() => setMode(o.v)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                    mode === o.v ? "border-signal/50 bg-signal/10" : "border-border hover:bg-accent/50",
                  )}
                >
                  <span>{o.t}</span>
                  <span className="text-[11px] text-muted-foreground">{o.d}</span>
                </button>
              ))}
            </div>
            <SliderRow label="Top-K evidence chunks" value={topK} min={1} max={10} onChange={setTopK} />
            <SliderRow label="Graph traversal depth" value={depth} min={1} max={4} onChange={setDepth} />
            <Button
              variant="outline"
              className="mt-6 w-full"
              onClick={() => setChatMessages(() => [greetingMessage(fullName, mode)])}
            >
              <Trash2 className="h-3.5 w-3.5" /> Clear chat history
            </Button>
          </div>
        </aside>
      </div>
    </>
  );
}

function SliderRow({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <div className="mt-5">
      <div className="mb-2.5 flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{value}</span>
      </div>
      <Slider min={min} max={max} step={1} value={[value]} onValueChange={([v]) => onChange(v)} />
    </div>
  );
}

function Message({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-secondary px-4 py-2.5 text-sm">{msg.content}</div>
      </div>
    );
  }
  const meta = [
    msg.mode && `Mode: ${msg.mode}`,
    msg.model && `Model: ${msg.model}`,
    msg.latency != null && `Latency: ${msg.latency.toFixed(3)}s`,
  ].filter(Boolean);
  return (
    <div className="flex gap-3">
      <div className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border border-border bg-surface">
        <span className="h-2 w-2 rounded-full bg-signal" />
      </div>
      <div className="min-w-0 flex-1">
        <Markdown>{msg.content}</Markdown>
        {meta.length > 0 && <div className="mt-2 font-mono text-[11px] text-muted-foreground">{meta.join("  ·  ")}</div>}
        {(msg.citations.length > 0 || msg.paths.length > 0) && (
          <div className="mt-3 space-y-2">
            {msg.citations.length > 0 && (
              <Fold icon={<BookOpen className="h-3.5 w-3.5" />} label={`Verified source citations (${msg.citations.length})`}>
                <ul className="space-y-3">
                  {msg.citations.map((c) => (
                    <li key={c.id} className="text-xs">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">[Source {c.id}]</span>
                        <code className="font-mono text-foreground/80">
                          {c.file_path}:{c.start_line}-{c.end_line}
                        </code>
                        <span className="text-muted-foreground">relevance {c.score}</span>
                      </div>
                      <p className="mt-1 border-l-2 border-border pl-2.5 italic text-muted-foreground">{c.snippet}...</p>
                    </li>
                  ))}
                </ul>
              </Fold>
            )}
            {msg.paths.length > 0 && (
              <Fold icon={<GitFork className="h-3.5 w-3.5" />} label={`Traversed knowledge graph paths (${msg.paths.length})`}>
                <ul className="space-y-1.5">
                  {msg.paths.map((p, i) => (
                    <li key={i} className="font-mono text-[11.5px] text-foreground/80">
                      {p}
                    </li>
                  ))}
                </ul>
              </Fold>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Fold({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-lg border border-border">
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground">
        {icon}
        {label}
        <ChevronDown className={cn("ml-auto h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-border px-3 py-3">{children}</CollapsibleContent>
    </Collapsible>
  );
}
