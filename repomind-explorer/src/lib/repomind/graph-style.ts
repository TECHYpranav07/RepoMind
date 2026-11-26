import type { GraphEdge, GraphNode } from "./types";

// Data-visualisation palette (canvas needs concrete colors). Hue families match the
// original RepoMind legend so meaning carries over; tones are tuned for a graphite canvas.
export const NODE_COLORS: Record<string, string> = {
  Repository: "#8b8cf8",
  Module: "#a78bfa",
  File: "#60a5fa",
  Class: "#22d3ee",
  Function: "#34d399",
  Library: "#fbbf24",
  API: "#f472b6",
  Configuration: "#fb923c",
  Documentation: "#94a3b8",
  Test: "#f87171",
  Target: "#ef4444",
  DirectImpact: "#f97316",
  InferredImpact: "#eab308",
  Unknown: "#94a3b8",
};

export const EDGE_COLORS: Record<string, string> = {
  CONTAINS: "#64748b",
  IMPORTS: "#60a5fa",
  CALLS: "#34d399",
  DEPENDS_ON: "#fbbf24",
  IMPLEMENTS: "#a78bfa",
  CONFIGURES: "#fb923c",
  DOCUMENTS: "#94a3b8",
  TESTS: "#f87171",
  USES_API: "#f472b6",
};
export const DEFAULT_EDGE_COLOR = "#475569";

export type ImpactRole = "target" | "direct" | "inferred" | null;

export interface ImpactSets {
  target?: Set<string>;
  direct?: Set<string>;
  inferred?: Set<string>;
}

export function impactRole(id: string, s: ImpactSets): ImpactRole {
  if (s.target?.has(id)) return "target";
  if (s.direct?.has(id)) return "direct";
  if (s.inferred?.has(id)) return "inferred";
  return null;
}

/** Sizes follow the original visualizer: target 28, direct 22, inferred 18, Function/Documentation 14, others 20. */
export function nodeStyle(node: Pick<GraphNode, "id" | "type">, s: ImpactSets) {
  const role = impactRole(node.id, s);
  if (role === "target") return { color: NODE_COLORS.Target, size: 28, role };
  if (role === "direct") return { color: NODE_COLORS.DirectImpact, size: 22, role };
  if (role === "inferred") return { color: NODE_COLORS.InferredImpact, size: 18, role };
  const t = node.type || "Unknown";
  return {
    color: NODE_COLORS[t] ?? NODE_COLORS.Unknown,
    size: t === "Function" || t === "Documentation" ? 14 : 20,
    role,
  };
}

/**
 * Type filter: hide nodes whose type isn't selected — except targets and direct impacts,
 * which always stay visible. No selection means "show everything".
 */
export function filterGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  selectedTypes: string[] | undefined,
  s: ImpactSets,
) {
  const keep = nodes.filter((n) => {
    if (!selectedTypes || selectedTypes.length === 0) return true;
    const t = n.type || "Unknown";
    return selectedTypes.includes(t) || s.target?.has(n.id) || s.direct?.has(n.id);
  });
  const ids = new Set(keep.map((n) => n.id));
  return { nodes: keep, edges: edges.filter((e) => ids.has(e.source) && ids.has(e.target)) };
}

/** Relation labels are drawn on edges only for small graphs (fewer than 40 edges). */
export const showEdgeLabels = (edgeCount: number) => edgeCount < 40;

export type PhysicsPreset = "jiggly" | "floating" | "calm";

export const PHYSICS_LABELS: { value: PhysicsPreset; label: string; hint: string }[] = [
  { value: "jiggly", label: "Jiggly & springy", hint: "Elastic bounce when you drag" },
  { value: "floating", label: "Floating & drifting", hint: "Gentle continuous drift" },
  { value: "calm", label: "Calm & settled", hint: "Settles fast and stays put" },
];

export interface PhysicsConfig {
  charge: number;
  centerStrength: number;
  linkStrength: number;
  velocityDecay: number;
  alphaDecay: number;
  cooldownTicks: number;
  drift: number;
  collidePadding: number;
  minDistance: number;
}

export function physicsFor(preset: PhysicsPreset, springLength: number): PhysicsConfig & { linkDistance: number } {
  if (preset === "floating") {
    return {
      linkDistance: Math.max(springLength, 80),
      charge: -260,
      centerStrength: 0.035,
      linkStrength: 0.35,
      velocityDecay: 0.18,
      alphaDecay: 0.006,
      cooldownTicks: Infinity,
      drift: 0.12,
      collidePadding: 6,
      minDistance: 80,
    };
  }
  if (preset === "calm") {
    return {
      linkDistance: Math.max(springLength, 80),
      charge: -300,
      centerStrength: 0.06,
      linkStrength: 0.6,
      velocityDecay: 0.55,
      alphaDecay: 0.05,
      cooldownTicks: 220,
      drift: 0,
      collidePadding: 5,
      minDistance: 80,
    };
  }
  return {
    linkDistance: Math.max(springLength, 90),
    charge: -340,
    centerStrength: 0.04,
    linkStrength: 0.7,
    velocityDecay: 0.22,
    alphaDecay: 0.018,
    cooldownTicks: Infinity,
    drift: 0,
    collidePadding: 7,
    minDistance: 90,
  };
}
