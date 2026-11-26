import { cn } from "@/lib/utils";

export function CodeBlock({
  code,
  lineNumbers = false,
  startLine = 1,
  className,
  maxHeight = 520,
}: {
  code: string;
  lineNumbers?: boolean;
  startLine?: number;
  className?: string;
  maxHeight?: number;
}) {
  const lines = code.replace(/\n$/, "").split("\n");
  return (
    <div
      className={cn("overflow-auto rounded-lg border border-border bg-surface font-mono text-[12.5px] leading-[1.65]", className)}
      style={{ maxHeight }}
    >
      <table className="w-full border-collapse">
        <tbody>
          {lines.map((l, i) => (
            <tr key={i} className="hover:bg-accent/40">
              {lineNumbers && (
                <td className="sticky left-0 select-none border-r border-border bg-surface px-3 text-right align-top text-muted-foreground/60">
                  {startLine + i}
                </td>
              )}
              <td className="whitespace-pre px-4 text-foreground/90">{l || " "}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
