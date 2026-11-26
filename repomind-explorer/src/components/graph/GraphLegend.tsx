import { EDGE_COLORS, NODE_COLORS } from "@/lib/repomind/graph-style";

export function TypeLegend({ types }: { types: string[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {types.map((t) => (
        <span key={t} className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ background: NODE_COLORS[t] ?? NODE_COLORS.Unknown }} />
          {t}
        </span>
      ))}
    </div>
  );
}

export function RelationLegend({ relations }: { relations: string[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 font-mono text-[11px] text-muted-foreground">
      {relations.map((r) => (
        <span key={r} className="inline-flex items-center gap-1.5">
          <span className="h-px w-4" style={{ background: EDGE_COLORS[r] ?? "#475569", height: 2 }} />
          {r}
        </span>
      ))}
    </div>
  );
}

export function ImpactLegend() {
  const items = [
    { c: NODE_COLORS.Target, l: "Target component" },
    { c: NODE_COLORS.DirectImpact, l: "Direct caller / importer" },
    { c: NODE_COLORS.InferredImpact, l: "Inferred / transitive caller" },
  ];
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs">
      {items.map((i) => (
        <span key={i.l} className="inline-flex items-center gap-2 font-medium" style={{ color: i.c }}>
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: i.c, boxShadow: `0 0 10px ${i.c}` }} />
          {i.l}
        </span>
      ))}
    </div>
  );
}
