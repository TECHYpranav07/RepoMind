import { forceCollide, forceX, forceY } from "d3-force";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from "react-force-graph-2d";
import { Maximize2, Minus, Pause, Play, Plus, Sparkles } from "lucide-react";

import {
  DEFAULT_EDGE_COLOR,
  EDGE_COLORS,
  nodeStyle,
  physicsFor,
  showEdgeLabels,
  type ImpactSets,
  type PhysicsPreset,
} from "@/lib/repomind/graph-style";
import type { GraphEdge, GraphNode } from "@/lib/repomind/types";
import { cn } from "@/lib/utils";

type N = NodeObject<GraphNode & { __r: number; __color: string; __role: string | null; __phase: number }>;
type L = LinkObject<N, { relation: string; __color: string; __key: string }>;

export interface KnowledgeGraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  impact?: ImpactSets;
  preset: PhysicsPreset;
  springLength: number;
  height: number;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

function hexA(hex: string, a: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

const KICKER: Record<string, string> = {
  target: "Target modification",
  direct: "Direct impact",
  inferred: "Inferred impact",
};

// Positions survive filter / preset changes so the layout morphs instead of jumping.
const positionCache = new Map<string, { x: number; y: number }>();

export default function KnowledgeGraphCanvas({
  nodes,
  edges,
  impact = {},
  preset,
  springLength,
  height,
  selectedId,
  onSelect,
}: KnowledgeGraphCanvasProps) {
  const fgRef = useRef<ForceGraphMethods<N, L> | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [multi, setMulti] = useState<Set<string>>(new Set());
  const [paused, setPaused] = useState(false);
  const [flow, setFlow] = useState(true);
  const fittedRef = useRef(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(320, Math.floor(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const graphData = useMemo(() => {
    const ns: N[] = nodes.map((n, i) => {
      const st = nodeStyle(n, impact);
      const cached = positionCache.get(n.id);
      return {
        ...n,
        __r: st.size * 0.42,
        __color: st.color,
        __role: st.role,
        __phase: (i * 2.399) % (Math.PI * 2),
        ...(cached ? { x: cached.x, y: cached.y } : {}),
      };
    });
    const ls: L[] = edges.map((e, i) => ({
      source: e.source,
      target: e.target,
      relation: e.relation,
      __color: EDGE_COLORS[e.relation] ?? DEFAULT_EDGE_COLOR,
      __key: `${e.source}->${e.target}#${i}`,
    }));
    fittedRef.current = false;
    return { nodes: ns, links: ls };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, impact.target, impact.direct, impact.inferred]);

  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of edges) {
      if (!m.has(e.source)) m.set(e.source, new Set());
      if (!m.has(e.target)) m.set(e.target, new Set());
      m.get(e.source)!.add(e.target);
      m.get(e.target)!.add(e.source);
    }
    return m;
  }, [edges]);

  const labelsOnEdges = showEdgeLabels(edges.length);
  const large = nodes.length > 600;

  // Focus = hovered node, else selected nodes. Everything else dims.
  const focus = useMemo(() => {
    const set = new Set<string>();
    const roots = hoverId ? [hoverId] : [...(selectedId ? [selectedId] : []), ...multi];
    for (const r of roots) {
      set.add(r);
      neighbors.get(r)?.forEach((x) => set.add(x));
    }
    return { roots: new Set(roots), set, active: roots.length > 0 };
  }, [hoverId, selectedId, multi, neighbors]);

  const phys = physicsFor(preset, springLength);

  // Apply physics whenever the preset, spacing or data change.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const charge = fg.d3Force("charge") as unknown as { strength: (v: number) => void; distanceMax?: (v: number) => void } | undefined;
    charge?.strength(phys.charge);
    charge?.distanceMax?.(phys.linkDistance * 6);
    const link = fg.d3Force("link") as unknown as
      | { distance: (v: number) => void; strength: (fn: (l: L) => number) => void }
      | undefined;
    link?.distance(phys.linkDistance);
    link?.strength((l: L) => {
      const s = l.source as N;
      const t = l.target as N;
      const deg = Math.min(neighbors.get(s.id as string)?.size ?? 1, neighbors.get(t.id as string)?.size ?? 1);
      return phys.linkStrength / Math.max(1, Math.sqrt(deg));
    });
    fg.d3Force("center", null as never);
    fg.d3Force("x", forceX(0).strength(phys.centerStrength) as never);
    fg.d3Force("y", forceY(0).strength(phys.centerStrength) as never);
    fg.d3Force("collide", forceCollide<N>((n) => n.__r + phys.collidePadding).strength(0.9) as never);
    if (phys.drift > 0) {
      let ns: N[] = [];
      let t = 0;
      const drift = Object.assign(
        () => {
          t += 0.012;
          for (const n of ns) {
            n.vx = (n.vx ?? 0) + Math.cos(t + n.__phase) * phys.drift * 0.08;
            n.vy = (n.vy ?? 0) + Math.sin(t * 0.8 + n.__phase * 1.3) * phys.drift * 0.08;
          }
        },
        { initialize: (n: N[]) => (ns = n) },
      );
      fg.d3Force("drift", drift as never);
    } else {
      fg.d3Force("drift", null as never);
    }
    if (!paused) fg.d3ReheatSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset, springLength, graphData]);

  // Floating mode never cools down, so fit once shortly after load.
  useEffect(() => {
    const id = setTimeout(() => {
      if (!fittedRef.current) {
        fgRef.current?.zoomToFit(600, 60);
        fittedRef.current = true;
      }
    }, 1400);
    return () => clearTimeout(id);
  }, [graphData]);

  const togglePause = () => {
    const fg = fgRef.current;
    if (!fg) return;
    if (paused) {
      fg.resumeAnimation();
      fg.d3ReheatSimulation();
    } else {
      fg.pauseAnimation();
    }
    setPaused(!paused);
  };

  const zoomBy = (f: number) => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.zoom(fg.zoom() * f, 250);
  };

  const onKey = (e: React.KeyboardEvent) => {
    const fg = fgRef.current;
    if (!fg) return;
    const k = fg.zoom();
    const c = fg.centerAt() as unknown as { x: number; y: number };
    const step = 60 / k;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    if (moves[e.key]) {
      e.preventDefault();
      fg.centerAt(c.x + moves[e.key][0], c.y + moves[e.key][1], 150);
    } else if (e.key === "+" || e.key === "=") zoomBy(1.25);
    else if (e.key === "-") zoomBy(0.8);
    else if (e.key === "0") fg.zoomToFit(400, 60);
    else if (e.key === "Escape") setMulti(new Set());
  };

  const paintNode = useCallback(
    (node: N, ctx: CanvasRenderingContext2D, scale: number) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const r = node.__r;
      const id = node.id as string;
      const isRoot = focus.roots.has(id);
      const inFocus = !focus.active || focus.set.has(id);
      const alpha = inFocus ? 1 : 0.14;

      // soft halo
      const haloR = r * (isRoot ? 3.2 : node.__role ? 2.6 : 2);
      const g = ctx.createRadialGradient(x, y, r * 0.6, x, y, haloR);
      g.addColorStop(0, hexA(node.__color, (isRoot ? 0.45 : node.__role ? 0.35 : 0.18) * alpha));
      g.addColorStop(1, hexA(node.__color, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, haloR, 0, Math.PI * 2);
      ctx.fill();

      // body
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = hexA(node.__color, 0.22 * alpha + 0.02);
      ctx.fill();
      ctx.lineWidth = (isRoot ? 2.4 : 1.4) / Math.max(scale, 0.6);
      ctx.strokeStyle = hexA(node.__color, alpha);
      ctx.stroke();
      // core
      ctx.beginPath();
      ctx.arc(x, y, r * 0.42, 0, Math.PI * 2);
      ctx.fillStyle = hexA(node.__color, alpha);
      ctx.fill();

      if (isRoot) {
        ctx.beginPath();
        ctx.arc(x, y, r + 4 / scale, 0, Math.PI * 2);
        ctx.lineWidth = 1 / scale;
        ctx.strokeStyle = "rgba(255,255,255,0.75)";
        ctx.stroke();
      }

      // label
      const showLabel = (focus.active ? focus.set.has(id) : true) && (scale > 0.55 || isRoot || (!large && r >= 8));
      if (showLabel) {
        const fs = Math.max(11 / scale, 2.5);
        ctx.font = `${isRoot ? 600 : 500} ${fs}px Geist, system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        const label = String(node.name ?? id);
        const ty = y + r + 3 / scale;
        ctx.lineWidth = 3 / scale;
        ctx.strokeStyle = "rgba(15,17,22,0.85)";
        ctx.strokeText(label, x, ty);
        ctx.fillStyle = inFocus ? "rgba(241,245,249,0.95)" : "rgba(241,245,249,0.2)";
        ctx.fillText(label, x, ty);
      }
    },
    [focus, large],
  );

  const linkActive = useCallback(
    (l: L) => {
      const s = (l.source as N).id as string;
      const t = (l.target as N).id as string;
      return focus.active && (focus.roots.has(s) || focus.roots.has(t));
    },
    [focus],
  );

  const paintLinkLabel = useCallback(
    (l: L, ctx: CanvasRenderingContext2D, scale: number) => {
      if (!labelsOnEdges) return;
      const s = l.source as N;
      const t = l.target as N;
      if (s.x == null || t.x == null || s.y == null || t.y == null) return;
      if (focus.active && !linkActive(l)) return;
      const cp = (l as L & { __controlPoints?: number[] }).__controlPoints;
      let mx = (s.x + t.x) / 2;
      let my = (s.y + t.y) / 2;
      if (cp && cp.length === 2) {
        mx = 0.25 * s.x + 0.5 * cp[0] + 0.25 * t.x;
        my = 0.25 * s.y + 0.5 * cp[1] + 0.25 * t.y;
      }
      const fs = Math.max(8.5 / scale, 2);
      ctx.font = `500 ${fs}px "Geist Mono", ui-monospace, monospace`;
      const w = ctx.measureText(l.relation).width;
      ctx.fillStyle = "rgba(18,20,26,0.88)";
      const ph = fs * 0.45;
      ctx.beginPath();
      ctx.roundRect(mx - w / 2 - ph, my - fs / 2 - ph * 0.6, w + ph * 2, fs + ph * 1.2, fs * 0.4);
      ctx.fill();
      ctx.fillStyle = hexA(l.__color, 0.95);
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(l.relation, mx, my + fs * 0.04);
    },
    [labelsOnEdges, focus, linkActive],
  );

  const nodeTooltip = useCallback((n: N) => {
    const loc = n.file_path ? `${n.file_path}:${n.line_number ?? ""}` : "Repository-level";
    const doc = (n.docstring || "").trim().slice(0, 100);
    const kicker = n.__role ? KICKER[n.__role] : n.type;
    return `<div class="graph-tooltip"><div class="gt-kicker" style="color:${n.__color}">● ${esc(kicker)}</div><div class="gt-name">${esc(n.name)}</div>${
      n.__role ? `<div class="gt-loc">ID: ${esc(n.id)}</div>` : `<div class="gt-loc">Type: ${esc(n.type)}</div>`
    }<div class="gt-loc">${esc(loc)}</div>${doc ? `<div class="gt-doc">${esc(doc)}</div>` : ""}</div>`;
  }, []);

  return (
    <div
      ref={wrapRef}
      tabIndex={0}
      onKeyDown={onKey}
      className="relative overflow-hidden rounded-xl border border-border bg-surface outline-none focus-visible:ring-2 focus-visible:ring-ring"
      style={{ height }}
      aria-label="Interactive knowledge graph. Drag nodes, scroll to zoom, arrow keys to pan."
    >
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" />
      <ForceGraph2D<N, L>
        ref={fgRef}
        width={width}
        height={height}
        graphData={graphData}
        backgroundColor="rgba(0,0,0,0)"
        nodeId="id"
        nodeRelSize={1}
        nodeVal={(n) => n.__r * n.__r}
        nodeLabel={nodeTooltip}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(n, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(n.x ?? 0, n.y ?? 0, n.__r + 3, 0, Math.PI * 2);
          ctx.fill();
        }}
        linkLabel={(l) => `<div class="graph-tooltip"><span class="gt-kicker">Relation</span><div class="gt-name" style="color:${l.__color}">${esc(l.relation)}</div></div>`}
        linkColor={(l) => (focus.active ? (linkActive(l) ? hexA(l.__color, 0.95) : hexA(l.__color, 0.06)) : hexA(l.__color, 0.42))}
        linkWidth={(l) => (linkActive(l) ? 2.2 : 1)}
        linkCurvature={0.12}
        linkDirectionalArrowLength={(l) => (linkActive(l) ? 5 : 3.5)}
        linkDirectionalArrowRelPos={0.92}
        linkDirectionalArrowColor={(l) => (focus.active && !linkActive(l) ? hexA(l.__color, 0.06) : hexA(l.__color, 0.85))}
        linkDirectionalParticles={(l) => (!flow || large ? 0 : linkActive(l) ? 3 : focus.active ? 0 : 1)}
        linkDirectionalParticleSpeed={(l) => (linkActive(l) ? 0.012 : 0.0045)}
        linkDirectionalParticleWidth={(l) => (linkActive(l) ? 3 : 1.6)}
        linkDirectionalParticleColor={(l) => hexA(l.__color, 0.95)}
        linkCanvasObjectMode={() => "after"}
        linkCanvasObject={paintLinkLabel}
        d3VelocityDecay={phys.velocityDecay}
        d3AlphaDecay={phys.alphaDecay}
        d3AlphaMin={preset === "floating" ? 0 : 0.001}
        cooldownTicks={phys.cooldownTicks}
        cooldownTime={preset === "floating" ? Infinity : 20000}
        warmupTicks={positionCache.size ? 0 : 30}
        autoPauseRedraw={false}
        minZoom={0.15}
        maxZoom={8}
        onEngineTick={() => {
          for (const n of graphData.nodes) if (n.x != null && n.y != null) positionCache.set(n.id as string, { x: n.x, y: n.y });
        }}
        onEngineStop={() => {
          if (!fittedRef.current) {
            fgRef.current?.zoomToFit(600, 60);
            fittedRef.current = true;
          }
        }}
        onNodeHover={(n) => {
          setHoverId(n ? (n.id as string) : null);
          if (wrapRef.current) wrapRef.current.style.cursor = n ? "pointer" : "grab";
        }}
        onNodeClick={(n, ev) => {
          const id = n.id as string;
          if (ev.ctrlKey || ev.metaKey || ev.shiftKey) {
            setMulti((prev) => {
              const next = new Set(prev);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              return next;
            });
          } else {
            setMulti(new Set());
          }
          onSelect?.(id);
        }}
        onBackgroundClick={() => setMulti(new Set())}
        onNodeDragEnd={(n) => {
          // release so springs pull it back — the "jiggly" bounce
          n.fx = undefined;
          n.fy = undefined;
        }}
      />

      <div className="absolute right-3 top-3 flex flex-col gap-1.5">
        <GraphButton label="Zoom in" onClick={() => zoomBy(1.3)}>
          <Plus className="h-3.5 w-3.5" />
        </GraphButton>
        <GraphButton label="Zoom out" onClick={() => zoomBy(0.77)}>
          <Minus className="h-3.5 w-3.5" />
        </GraphButton>
        <GraphButton label="Fit to view" onClick={() => fgRef.current?.zoomToFit(500, 60)}>
          <Maximize2 className="h-3.5 w-3.5" />
        </GraphButton>
        <GraphButton label={paused ? "Resume motion" : "Freeze motion"} onClick={togglePause}>
          {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
        </GraphButton>
        <GraphButton label={flow ? "Hide edge flow" : "Show edge flow"} active={flow} onClick={() => setFlow(!flow)}>
          <Sparkles className="h-3.5 w-3.5" />
        </GraphButton>
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-border/60 bg-background/70 px-2.5 py-1.5 font-mono text-[10.5px] text-muted-foreground backdrop-blur">
        {nodes.length} nodes · {edges.length} edges
        {multi.size > 0 && <span className="text-foreground"> · {multi.size + (selectedId && !multi.has(selectedId) ? 1 : 0)} selected</span>}
      </div>
      <div className="pointer-events-none absolute bottom-3 right-3 hidden rounded-md px-2 py-1 text-[10.5px] text-muted-foreground/80 md:block">
        Drag · scroll to zoom · ⌘/Shift-click to multi-select · arrows pan
      </div>
    </div>
  );
}

function GraphButton({
  label,
  onClick,
  active,
  children,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "grid h-8 w-8 place-items-center rounded-md border border-border bg-background/80 text-muted-foreground backdrop-blur transition-colors hover:bg-accent hover:text-foreground",
        active && "text-signal",
      )}
    >
      {children}
    </button>
  );
}
