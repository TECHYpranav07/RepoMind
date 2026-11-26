import type { BenchmarkRow, ChatMode } from "./types";

/** Keep the first N question ids (dataset order) for the selected modes — identical to running with N questions. */
export function sliceBenchmarkRows(rows: BenchmarkRow[], modes: ChatMode[], n: number): BenchmarkRow[] {
  const ids: string[] = [];
  for (const r of rows) if (!ids.includes(r.question_id)) ids.push(r.question_id);
  const keep = new Set(ids.slice(0, n));
  const wanted = new Set(modes.map((m) => m.toUpperCase()));
  return rows.filter((r) => keep.has(r.question_id) && wanted.has(String(r.mode).toUpperCase()));
}

export const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** pandas groupby("mode").mean(): NaN/None values are skipped; all-missing -> null. Modes sorted. */
export function aggregateByMode(rows: BenchmarkRow[], cols: string[]) {
  const modes = Array.from(new Set(rows.map((r) => String(r.mode).toUpperCase()))).sort();
  return modes.map((mode) => {
    const subset = rows.filter((r) => String(r.mode).toUpperCase() === mode);
    const out: Record<string, number | null> & { mode?: never } = {};
    for (const c of cols) {
      const vals = subset.map((r) => r[c]).filter(isNum);
      out[c] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    }
    return { mode, values: out };
  });
}

export function modeRow(rows: BenchmarkRow[], mode: "GRAPH" | "HYBRID", cols: string[]) {
  return aggregateByMode(rows, cols).find((a) => a.mode === mode)?.values ?? null;
}

export type Winner = "tie" | "hybrid" | "graph" | null;

/** Same rule as the evaluation page: |diff| under threshold ties, else direction decides. */
export function pickWinner(
  graph: number | null | undefined,
  hybrid: number | null | undefined,
  higherIsBetter: boolean,
  threshold: number,
): Winner {
  if (!isNum(graph) || !isNum(hybrid)) return null;
  const diff = hybrid - graph;
  if (Math.abs(diff) < threshold) return "tie";
  if ((diff > 0 && higherIsBetter) || (diff < 0 && !higherIsBetter)) return "hybrid";
  return "graph";
}

export const KPI_THRESHOLD = { score: 0.001, latency: 0.05 };
export const MATRIX_THRESHOLD = { score: 0.005, latency: 0.05 };

export const MATRIX_METRICS: {
  key: string;
  label: string;
  higherIsBetter: boolean;
  unit: "%" | "s";
}[] = [
  { key: "recall_at_k", label: "Retrieval Recall", higherIsBetter: true, unit: "%" },
  { key: "precision_at_k", label: "Retrieval Precision", higherIsBetter: true, unit: "%" },
  { key: "impact_f1", label: "Impact Detection F1", higherIsBetter: true, unit: "%" },
  { key: "correctness", label: "Answer Correctness", higherIsBetter: true, unit: "%" },
  { key: "faithfulness", label: "Answer Faithfulness", higherIsBetter: true, unit: "%" },
  { key: "total_latency_s", label: "Total Latency", higherIsBetter: false, unit: "s" },
];

export interface MatrixRow {
  label: string;
  graph: number;
  hybrid: number;
  unit: "%" | "s";
  winner: Exclude<Winner, null>;
  takeaway: string;
}

export function buildMatrix(rows: BenchmarkRow[]) {
  const cols = MATRIX_METRICS.map((m) => m.key);
  const g = modeRow(rows, "GRAPH", cols);
  const h = modeRow(rows, "HYBRID", cols);
  const out: MatrixRow[] = [];
  let hWins = 0;
  let gWins = 0;
  for (const m of MATRIX_METRICS) {
    const gv = g?.[m.key];
    const hv = h?.[m.key];
    if (!isNum(gv) || !isNum(hv)) continue;
    const isLat = m.unit === "s";
    const w = pickWinner(gv, hv, m.higherIsBetter, isLat ? MATRIX_THRESHOLD.latency : MATRIX_THRESHOLD.score)!;
    const diff = Math.abs(hv - gv);
    let takeaway = "Comparable performance";
    if (w === "hybrid") {
      hWins++;
      takeaway = isLat ? `Hybrid ${diff.toFixed(3)}s faster` : `Hybrid +${pct(diff)}`;
    } else if (w === "graph") {
      gWins++;
      takeaway = isLat ? `Graph ${diff.toFixed(3)}s faster` : `GraphRAG +${pct(diff)}`;
    }
    out.push({ label: m.label, graph: gv, hybrid: hv, unit: m.unit, winner: w, takeaway });
  }
  const total = out.length;
  let verdict: { tone: "hybrid" | "graph" | "tie"; text: string };
  if (hWins > gWins)
    verdict = {
      tone: "hybrid",
      text: `Hybrid GraphRAG leads across ${hWins} of ${total} key metrics with superior recall and context grounding.`,
    };
  else if (gWins > hWins)
    verdict = {
      tone: "graph",
      text: `GraphRAG leads across ${gWins} of ${total} key metrics with tighter deterministic AST precision.`,
    };
  else
    verdict = {
      tone: "tie",
      text: "Balanced trade-off: GraphRAG offers faster AST precision, while Hybrid offers broader semantic discovery.",
    };
  return { rows: out, verdict, hasAny: Boolean(g || h) };
}

/** Python-style "{:.1%}". */
export function pct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits)}%`;
}

export function fmtMetric(v: unknown, unit: "%" | "s") {
  if (!isNum(v)) return "N/A";
  return unit === "s" ? `${v.toFixed(3)}s` : pct(v);
}

export function asList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(String);
  if (typeof v === "string") return v.split(",").map((s) => s.trim()).filter(Boolean);
  return [];
}

// ───────────── CSV export (mirrors pandas DataFrame.to_csv(index=False)) ─────────────

function pyRepr(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v);
  if (Array.isArray(v)) return `[${v.map((x) => (typeof x === "string" ? `'${x.replace(/'/g, "\\'")}'` : pyRepr(x))).join(", ")}]`;
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function csvCell(s: string) {
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function rowsToCsv(rows: BenchmarkRow[]): string {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0]);
  const lines = [cols.map(csvCell).join(",")];
  for (const r of rows) lines.push(cols.map((c) => csvCell(pyRepr(r[c]))).join(","));
  return lines.join("\n") + "\n";
}
