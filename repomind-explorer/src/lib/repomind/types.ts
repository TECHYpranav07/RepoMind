// Shapes returned by backend/api_server.py (which wraps the RepoMind Python engine).

export interface RepoMeta {
  owner: string;
  name: string;
  full_name: string;
  description?: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  default_branch: string;
  language: string;
  license?: string | null;
  html_url: string;
  clone_url: string;
  is_local: boolean;
}

export interface RepoSummary {
  repo_loaded: boolean;
  meta?: RepoMeta;
  files?: number;
  chunks?: number;
  nodes?: number;
  edges?: number;
  lines_of_code?: number;
  node_type_breakdown?: Record<string, number>;
  edge_relation_breakdown?: Record<string, number>;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  file_path?: string | null;
  line_number?: number | null;
  docstring?: string | null;
  source_snippet?: string | null;
  in_degree?: number;
  out_degree?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_type_breakdown: Record<string, number>;
  edge_relation_breakdown: Record<string, number>;
  density: number;
  top_hubs: { id: string; name: string; type: string; in_degree: number; out_degree: number }[];
}

export interface LibraryRow {
  name: string;
  specifier: string;
  source: string;
}

export interface GraphResponse extends GraphData {
  stats: GraphStats;
  libraries: LibraryRow[];
}

export interface RepoFileInfo {
  path: string;
  name: string;
  extension: string;
  file_type: string;
  size_bytes: number;
  line_count: number;
}

export interface RepoFile extends RepoFileInfo {
  content: string;
}

export interface Citation {
  id: number;
  file_path: string;
  start_line: number;
  end_line: number;
  entity?: string;
  score: number;
  snippet: string;
}

export type ChatMode = "hybrid" | "graph";

export interface ChatRequest {
  query: string;
  mode: ChatMode;
  top_k: number;
  graph_depth: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  graph_paths: string[];
  latency: number;
  model_used: string;
  mode: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  paths: string[];
  mode?: string;
  model?: string;
  latency?: number | null;
}

export interface Scenario {
  label: string;
  query: string;
}

export interface ImpactEntity {
  id: string;
  name: string;
  type: string;
  file_path?: string | null;
  line_number?: number | null;
  docstring?: string | null;
}

export interface ImpactPath {
  from: string;
  to: string;
  relation: string;
  path_text: string;
  depth: number;
  is_direct: boolean;
}

export interface WhatIfResult {
  hypothesis: string;
  action: string;
  target_entity: string;
  replacement_entity?: string | null;
  risk_level: "High" | "Medium" | "Low" | string;
  report_markdown: string;
  target_nodes: ImpactEntity[];
  direct_affected: ImpactEntity[];
  inferred_affected: ImpactEntity[];
  tests_to_update: ImpactEntity[];
  configs_to_update: ImpactEntity[];
  impact_paths: ImpactPath[];
  citations: Citation[];
  impact_subgraph: GraphData;
  latency: number;
  model_used: string;
  export_markdown: string;
  export_json: Record<string, unknown>;
}

export type GtSource = "ast" | "curated";
export type SpeedMode = "fast" | "turbo";

export interface BenchmarkRequest {
  modes: ChatMode[];
  num_questions: number;
  gt_source: GtSource;
  speed_mode: SpeedMode;
}

export interface BenchmarkRow {
  question_id: string;
  question: string;
  category: string;
  mode: string;
  expected_files: string[] | string;
  expected_components: string[] | string;
  reference_answer: string;
  retrieved_files: string[] | string;
  retrieved_components: string[] | string;
  generated_answer: string;
  prompt_context: string;
  graph_paths: string[];
  precision_at_k: number | null;
  recall_at_k: number | null;
  impact_precision: number | null;
  impact_recall: number | null;
  impact_f1: number | null;
  impact_tp: number | null;
  impact_fp: number | null;
  impact_fn: number | null;
  impact_unannotated: boolean;
  correctness: number | null;
  faithfulness: number | null;
  retrieval_latency_s: number | null;
  llm_latency_s: number | null;
  total_latency_s: number | null;
  context_chars: number | null;
  estimated_tokens: number | null;
  status: string;
  error: string | null;
  [key: string]: unknown;
}

export interface Progress {
  message: string;
  progress: number;
}
