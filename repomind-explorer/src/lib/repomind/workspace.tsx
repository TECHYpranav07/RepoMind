import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createDemoClient, createLiveClient, type RepoMindClient } from "./client";
import type { BenchmarkRow, ChatMessage, ChatMode, Progress, RepoSummary, WhatIfResult } from "./types";

export interface Connection {
  mode: "demo" | "live";
  url: string;
}

const STORAGE_KEY = "repomind.connection";
const DEFAULT_URL = (import.meta.env.VITE_REPOMIND_API_URL as string | undefined) || "http://localhost:8000";

export function greetingMessage(fullName: string, mode: ChatMode): ChatMessage {
  return {
    id: `greet-${Date.now()}`,
    role: "assistant",
    content: `Hello! I am **RepoMind**. I have parsed \`${fullName}\` into a knowledge graph and vector index. Ask me anything about how this codebase is structured, or switch to the **What-If Analysis** page to test hypothetical refactorings!`,
    citations: [],
    paths: [],
    mode: mode.toUpperCase(),
    model: "RepoMind Engine",
    latency: null,
  };
}

interface IngestState {
  running: boolean;
  progress: Progress | null;
  error: string | null;
  success: string | null;
}

interface WorkspaceValue {
  connection: Connection;
  setConnection: (c: Connection) => void;
  client: RepoMindClient;
  summary: RepoSummary | null;
  summaryError: string | null;
  /** Incremented whenever a new repository is loaded so pages refetch. */
  repoVersion: number;
  ingest: IngestState;
  runIngest: (target: string) => Promise<void>;
  // Per-repo state (cleared on every new ingestion, like the Streamlit session).
  chatMessages: ChatMessage[];
  setChatMessages: (fn: (m: ChatMessage[]) => ChatMessage[]) => void;
  whatifResult: WhatIfResult | null;
  setWhatifResult: (r: WhatIfResult | null) => void;
  whatifInput: string;
  setWhatifInput: (s: string) => void;
  benchmark: { rows: BenchmarkRow[] | null; lastRun: Date | null; status: string | null };
  setBenchmark: (b: { rows: BenchmarkRow[] | null; lastRun: Date | null; status: string | null }) => void;
}

const Ctx = createContext<WorkspaceValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [connection, setConnectionState] = useState<Connection>({ mode: "live", url: DEFAULT_URL });
  const [summary, setSummary] = useState<RepoSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [repoVersion, setRepoVersion] = useState(0);
  const [ingest, setIngest] = useState<IngestState>({ running: false, progress: null, error: null, success: null });
  const [chatMessages, setChatMessagesState] = useState<ChatMessage[]>([]);
  const [whatifResult, setWhatifResult] = useState<WhatIfResult | null>(null);
  const [whatifInput, setWhatifInput] = useState("What if we replace FAISS with ChromaDB?");
  const [benchmark, setBenchmark] = useState<WorkspaceValue["benchmark"]>({ rows: null, lastRun: null, status: null });

  // Read saved connection after hydration.
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setConnectionState(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, []);

  const client = useMemo(
    () => (connection.mode === "live" ? createLiveClient(connection.url) : createDemoClient()),
    [connection.mode, connection.url],
  );

  const resetRepoState = useCallback(() => {
    setChatMessagesState([]);
    setWhatifResult(null);
    setBenchmark({ rows: null, lastRun: null, status: null });
  }, []);

  const clientRef = useRef(client);
  clientRef.current = client;

  // Load whatever repository the engine currently has (the server auto-loads the sample on start).
  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    setSummaryError(null);
    resetRepoState();
    client
      .getState()
      .then((s) => {
        if (cancelled) return;
        setSummary(s);
        setRepoVersion((v) => v + 1);
      })
      .catch((e: Error) => !cancelled && setSummaryError(e.message));
    return () => {
      cancelled = true;
    };
  }, [client, resetRepoState]);

  const setConnection = useCallback((c: Connection) => {
    setConnectionState(c);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
    } catch {
      /* ignore */
    }
  }, []);

  const runIngest = useCallback(
    async (target: string) => {
      setIngest({ running: true, progress: { message: "Connecting to repository source...", progress: 0 }, error: null, success: null });
      try {
        const s = await clientRef.current.ingest(target, (p) =>
          setIngest((prev) => ({ ...prev, progress: p })),
        );
        resetRepoState();
        setSummary(s);
        setSummaryError(null);
        setRepoVersion((v) => v + 1);
        setIngest({
          running: false,
          progress: { message: "Repository successfully analyzed and indexed!", progress: 1 },
          error: null,
          success: `Successfully processed ${s.meta?.full_name} with ${s.files} files, ${s.chunks} chunks, and ${s.nodes} graph entities!`,
        });
      } catch (e) {
        setIngest({ running: false, progress: null, error: (e as Error).message, success: null });
      }
    },
    [resetRepoState],
  );

  const setChatMessages = useCallback((fn: (m: ChatMessage[]) => ChatMessage[]) => setChatMessagesState(fn), []);

  const value: WorkspaceValue = {
    connection,
    setConnection,
    client,
    summary,
    summaryError,
    repoVersion,
    ingest,
    runIngest,
    chatMessages,
    setChatMessages,
    whatifResult,
    setWhatifResult,
    whatifInput,
    setWhatifInput,
    benchmark,
    setBenchmark,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWorkspace() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return v;
}
