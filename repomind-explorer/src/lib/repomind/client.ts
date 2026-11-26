import type {
  BenchmarkRequest,
  BenchmarkRow,
  ChatRequest,
  ChatResponse,
  GraphResponse,
  Progress,
  RepoFile,
  RepoFileInfo,
  RepoSummary,
  Scenario,
  WhatIfResult,
} from "./types";
import { sliceBenchmarkRows } from "./benchmark";

/** One interface, two sources: the live RepoMind server, or the recorded sample snapshot. */
export interface RepoMindClient {
  kind: "live" | "demo";
  getState(): Promise<RepoSummary>;
  ingest(target: string, onProgress: (p: Progress) => void): Promise<RepoSummary>;
  getGraph(): Promise<GraphResponse>;
  listFiles(): Promise<RepoFileInfo[]>;
  getFile(path: string): Promise<RepoFile>;
  chatSuggestions(): Promise<string[]>;
  chat(req: ChatRequest): Promise<ChatResponse>;
  whatifScenarios(): Promise<Scenario[]>;
  whatif(hypothesis: string, maxDepth: number): Promise<WhatIfResult>;
  runBenchmark(req: BenchmarkRequest, onProgress: (p: Progress) => void): Promise<BenchmarkRow[]>;
}

export class ApiError extends Error {}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ─────────────────────────────── live ───────────────────────────────

export function createLiveClient(baseUrl: string): RepoMindClient {
  const base = baseUrl.replace(/\/+$/, "");

  async function req<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${base}/api${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      });
    } catch {
      throw new ApiError(`Can't reach the RepoMind server at ${base}. Is it running?`);
    }
    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* keep default */
      }
      throw new ApiError(detail);
    }
    return res.json() as Promise<T>;
  }

  async function pollJob<T>(jobId: string, onProgress: (p: Progress) => void): Promise<T> {
    for (;;) {
      const job = await req<{
        status: string;
        progress: number;
        message: string;
        error?: string | null;
        result?: T;
      }>(`/jobs/${jobId}`);
      onProgress({ message: job.message, progress: job.progress });
      if (job.status === "done") return job.result as T;
      if (job.status === "error") throw new ApiError(job.error || "Job failed");
      await sleep(500);
    }
  }

  return {
    kind: "live",
    getState: () => req("/state"),
    async ingest(target, onProgress) {
      const { job_id } = await req<{ job_id: string }>("/ingest", {
        method: "POST",
        body: JSON.stringify({ target }),
      });
      return pollJob<RepoSummary>(job_id, onProgress);
    },
    getGraph: () => req("/graph"),
    listFiles: () => req("/files"),
    getFile: (path) => req(`/files/content?path=${encodeURIComponent(path)}`),
    chatSuggestions: () => req("/chat/suggestions"),
    chat: (body) => req("/chat", { method: "POST", body: JSON.stringify(body) }),
    whatifScenarios: () => req("/whatif/scenarios"),
    whatif: (hypothesis, max_depth) =>
      req("/whatif", { method: "POST", body: JSON.stringify({ hypothesis, max_depth }) }),
    async runBenchmark(body, onProgress) {
      const { job_id } = await req<{ job_id: string }>("/benchmark", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const res = await pollJob<{ rows: BenchmarkRow[] }>(job_id, onProgress);
      return res.rows;
    },
  };
}

// ─────────────────────────────── demo ───────────────────────────────

interface Snapshot {
  state: RepoSummary;
  graph: GraphResponse;
  files: RepoFile[];
  suggestions: string[];
  scenarios: Scenario[];
  chat: { answers: ChatResponse[]; index: Record<string, number> };
  whatif: Record<string, WhatIfResult>;
  benchmark: Record<"ast" | "curated", BenchmarkRow[]>;
}

export const DEMO_TARGETS = ["sample", "sample_repo", "ragcraft"];
export const DEMO_LIMIT_MESSAGE =
  "The built-in sample only includes recorded results for the suggested prompts. Connect your RepoMind server to run your own.";

let snapshotPromise: Promise<Snapshot> | null = null;
function loadSnapshot(): Promise<Snapshot> {
  if (!snapshotPromise) {
    snapshotPromise = fetch("/demo/repomind-sample.json").then((r) => {
      if (!r.ok) throw new ApiError("Couldn't load the built-in sample data.");
      return r.json();
    });
  }
  return snapshotPromise;
}

export function createDemoClient(): RepoMindClient {
  return {
    kind: "demo",
    async getState() {
      return (await loadSnapshot()).state;
    },
    async ingest(target, onProgress) {
      const t = target.trim();
      if (!DEMO_TARGETS.includes(t)) {
        throw new ApiError(
          "Ingestion Error: analyzing other repositories needs your RepoMind server. Connect it from the sidebar, or load the built-in RagCraft repo.",
        );
      }
      const s = await loadSnapshot();
      const st = s.state;
      const steps: Progress[] = [
        { message: "Connecting to repository source...", progress: 0.05 },
        { message: `Fetched metadata for ${st.meta?.full_name}`, progress: 0.2 },
        { message: `Ingested ${st.files} files. Chunking...`, progress: 0.6 },
        { message: `Generated ${st.chunks} semantic chunks. Extracting Knowledge Graph...`, progress: 0.7 },
        {
          message: `Constructed Knowledge Graph: ${st.nodes} nodes, ${st.edges} edges.`,
          progress: 0.8,
        },
        { message: "Generating vector embeddings and building FAISS index...", progress: 0.95 },
        { message: "Repository successfully analyzed and indexed!", progress: 1 },
      ];
      for (const step of steps) {
        onProgress(step);
        await sleep(260);
      }
      return st;
    },
    async getGraph() {
      return (await loadSnapshot()).graph;
    },
    async listFiles() {
      return (await loadSnapshot()).files.map(({ content: _c, ...rest }) => rest);
    },
    async getFile(path) {
      const f = (await loadSnapshot()).files.find((x) => x.path === path);
      if (!f) throw new ApiError("File not found");
      return f;
    },
    async chatSuggestions() {
      return (await loadSnapshot()).suggestions;
    },
    async chat(r) {
      const s = await loadSnapshot();
      await sleep(450);
      const idx = s.chat.index[`${r.query}|${r.mode}|${r.top_k}|${r.graph_depth}`];
      if (idx === undefined) throw new ApiError(DEMO_LIMIT_MESSAGE);
      return s.chat.answers[idx];
    },
    async whatifScenarios() {
      return (await loadSnapshot()).scenarios;
    },
    async whatif(hypothesis, maxDepth) {
      const s = await loadSnapshot();
      await sleep(600);
      const res = s.whatif[`${hypothesis.trim()}|${maxDepth}`];
      if (!res) throw new ApiError(DEMO_LIMIT_MESSAGE);
      return res;
    },
    async runBenchmark(r, onProgress) {
      const s = await loadSnapshot();
      const rows = sliceBenchmarkRows(s.benchmark[r.gt_source], r.modes, r.num_questions);
      const total = rows.length;
      for (let i = 1; i <= total; i++) {
        onProgress({ message: `Evaluated ${i}/${total} queries`, progress: i / total });
        await sleep(140);
      }
      return rows;
    },
  };
}
