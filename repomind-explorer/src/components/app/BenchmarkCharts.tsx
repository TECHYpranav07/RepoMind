import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { aggregateByMode, isNum, pct } from "@/lib/repomind/benchmark";
import type { BenchmarkRow } from "@/lib/repomind/types";

const METRIC_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
const axis = { stroke: "var(--muted-foreground)", fontSize: 11, tickLine: false, axisLine: false } as const;
const tooltipStyle = {
  contentStyle: {
    background: "var(--popover)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 12,
    color: "var(--popover-foreground)",
  },
  cursor: { fill: "color-mix(in oklab, var(--foreground) 5%, transparent)" },
};

function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4">
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-muted-foreground">{subtitle}</div>
      </div>
      {children}
    </div>
  );
}

export function ScoreChart({
  rows,
  metrics,
  title,
  subtitle,
}: {
  rows: BenchmarkRow[];
  metrics: [string, string][];
  title: string;
  subtitle: string;
}) {
  const agg = aggregateByMode(
    rows,
    metrics.map((m) => m[0]),
  );
  // Same layout as the original grouped bars: one bar per (metric, mode).
  const data = metrics.flatMap(([col, label], idx) =>
    agg.map((a) => {
      const v = a.values[col];
      return {
        name: `${a.mode} — ${label}`,
        value: isNum(v) ? v : 0,
        text: isNum(v) ? pct(v) : "N/A",
        color: METRIC_COLORS[idx % METRIC_COLORS.length],
      };
    }),
  );
  const h = Math.max(200, data.length * 38 + 30);
  return (
    <ChartCard title={title} subtitle={subtitle}>
      <ResponsiveContainer width="100%" height={h}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 48, top: 0, bottom: 0 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 1.15]} tickFormatter={(v) => `${Math.round(v * 100)}%`} ticks={[0, 0.25, 0.5, 0.75, 1]} {...axis} />
          <YAxis type="category" dataKey="name" width={190} {...axis} tick={{ fill: "var(--foreground)", fontSize: 11 }} />
          <Tooltip {...tooltipStyle} formatter={(_v, _n, p) => [(p.payload as { text: string }).text, "Score"]} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={700}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.color} />
            ))}
            <LabelList dataKey="text" position="right" style={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        {metrics.map(([, l], i) => (
          <span key={l} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ background: METRIC_COLORS[i] }} />
            {l}
          </span>
        ))}
      </div>
    </ChartCard>
  );
}

export function LatencyChart({ rows }: { rows: BenchmarkRow[] }) {
  const cols: [string, string, string][] = [
    ["retrieval_latency_s", "Retrieval", "var(--chart-1)"],
    ["llm_latency_s", "LLM Generation", "var(--chart-3)"],
    ["total_latency_s", "Total End-to-End", "var(--chart-5)"],
  ];
  const agg = aggregateByMode(
    rows,
    cols.map((c) => c[0]),
  );
  const data = agg.map((a) => {
    const o: Record<string, number | string> = { mode: a.mode };
    for (const [c] of cols) o[c] = isNum(a.values[c]) ? (a.values[c] as number) : 0;
    return o;
  });
  return (
    <ChartCard title="Response time by mode" subtitle="Retrieval · LLM generation · total (seconds)">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ left: 0, right: 8, top: 20, bottom: 0 }} barGap={4}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="mode" {...axis} tick={{ fill: "var(--foreground)", fontSize: 11 }} />
          <YAxis {...axis} tickFormatter={(v) => `${v}s`} />
          <Tooltip {...tooltipStyle} formatter={(v: number) => `${v.toFixed(3)}s`} />
          <Legend iconType="square" iconSize={8} wrapperStyle={{ fontSize: 11, color: "var(--muted-foreground)" }} />
          {cols.map(([c, l, color]) => (
            <Bar key={c} dataKey={c} name={l} fill={color} radius={[4, 4, 0, 0]} animationDuration={700}>
              <LabelList dataKey={c} position="top" formatter={(v: number) => `${v.toFixed(3)}s`} style={{ fill: "var(--muted-foreground)", fontSize: 10 }} />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
