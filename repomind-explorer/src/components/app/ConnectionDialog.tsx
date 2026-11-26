import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useWorkspace } from "@/lib/repomind/workspace";
import { cn } from "@/lib/utils";

export function ConnectionDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { connection, setConnection } = useWorkspace();
  const [mode, setMode] = useState(connection.mode);
  const [url, setUrl] = useState(connection.url);
  const [test, setTest] = useState<"idle" | "testing" | "ok" | "fail">("idle");

  useEffect(() => {
    if (open) {
      setMode(connection.mode);
      setUrl(connection.url);
      setTest("idle");
    }
  }, [open, connection]);

  const runTest = async () => {
    setTest("testing");
    try {
      const r = await fetch(`${url.replace(/\/+$/, "")}/api/health`);
      setTest(r.ok ? "ok" : "fail");
    } catch {
      setTest("fail");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Engine connection</DialogTitle>
          <DialogDescription>
            Use the recorded RagCraft sample, or point the app at your running RepoMind server.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-2">
          {(
            [
              { v: "demo", t: "Built-in sample", d: "Recorded results, works instantly" },
              { v: "live", t: "RepoMind server", d: "Any repo, live analysis" },
            ] as const
          ).map((o) => (
            <button
              key={o.v}
              type="button"
              onClick={() => setMode(o.v)}
              className={cn(
                "rounded-lg border p-3 text-left transition-colors",
                mode === o.v ? "border-signal/60 bg-signal/10" : "border-border hover:bg-accent/50",
              )}
            >
              <div className="text-sm font-medium">{o.t}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{o.d}</div>
            </button>
          ))}
        </div>

        {mode === "live" && (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="api-url">Server address</Label>
              <div className="flex gap-2">
                <Input id="api-url" value={url} onChange={(e) => setUrl(e.target.value)} className="font-mono text-sm" />
                <Button variant="secondary" onClick={runTest} disabled={test === "testing"}>
                  {test === "testing" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Test"}
                </Button>
              </div>
              {test === "ok" && (
                <p className="flex items-center gap-1.5 text-xs text-success">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Server is reachable.
                </p>
              )}
              {test === "fail" && (
                <p className="flex items-center gap-1.5 text-xs text-danger">
                  <XCircle className="h-3.5 w-3.5" /> Couldn't reach the server at that address.
                </p>
              )}
            </div>
            <div className="rounded-lg border border-border bg-surface p-3 font-mono text-[11.5px] leading-relaxed text-muted-foreground">
              <div className="text-foreground/80"># in the RepoMind folder</div>
              <div>pip install fastapi uvicorn</div>
              <div>uvicorn api_server:app --port 8000</div>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setConnection({ mode, url: url.trim() || "http://localhost:8000" });
              onOpenChange(false);
            }}
          >
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
