import { lazy, Suspense } from "react";
import { ClientOnly } from "@tanstack/react-router";
import type { KnowledgeGraphCanvasProps } from "./KnowledgeGraphCanvas";

// The canvas library touches `window` at import time, so it loads only in the browser.
const Canvas = lazy(() => import("./KnowledgeGraphCanvas"));

export function KnowledgeGraph(props: KnowledgeGraphCanvasProps) {
  const fallback = (
    <div
      className="grid place-items-center rounded-xl border border-border bg-surface bg-grid text-sm text-muted-foreground"
      style={{ height: props.height }}
    >
      <span className="animate-rm-pulse">Laying out graph…</span>
    </div>
  );
  return (
    <ClientOnly fallback={fallback}>
      <Suspense fallback={fallback}>
        <Canvas {...props} />
      </Suspense>
    </ClientOnly>
  );
}
