import { useState } from "react";
import { Check, Copy, Terminal } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import type { ExecTrace } from "@/lib/realai/types";

function CopyBtn({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="inline-flex size-8 items-center justify-center rounded-sm text-mute transition-colors duration-150 hover:text-text"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1200);
        } catch {
          /* ignore */
        }
      }}
      aria-label="Copy output"
    >
      {done ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
    </button>
  );
}

export function ToolCard({ trace }: { trace: ExecTrace }) {
  const ok = trace.exitCode === 0 && !trace.timedOut && !trace.error;
  const headline =
    trace.command ||
    (trace.kind === "read" ? `read ${trace.path}` : null) ||
    (trace.kind === "write" ? `write ${trace.path}` : null) ||
    (trace.kind === "list" ? `list ${trace.path}` : null) ||
    trace.kind;
  const body = [trace.stdout, trace.stderr ? `stderr:\n${trace.stderr}` : ""]
    .filter(Boolean)
    .join("\n");

  return (
    <div className="overflow-hidden rounded-md bg-panel shadow-[var(--shadow-border)]">
      <div className="flex items-center gap-2 px-3 py-2">
        <Terminal className="size-3.5 shrink-0 text-acid" />
        <span className="font-mono text-xs text-mute uppercase tracking-widest">live exec</span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 font-mono text-xs tabular-nums",
            ok ? "text-acid" : "text-hot",
          )}
        >
          {trace.timedOut ? "timeout" : `exit ${trace.exitCode ?? "?"}`}
        </span>
        <span className="font-mono text-xs tabular-nums text-mute">{formatDuration(trace.durationMs)}</span>
        <div className="ml-auto">
          <CopyBtn text={body || headline} />
        </div>
      </div>
      <div className="border-t border-line px-3 py-2">
        <p className="font-mono text-xs text-ice break-all">{headline}</p>
        {trace.path && trace.command ? (
          <p className="mt-1 font-mono text-xs text-mute">{trace.path}</p>
        ) : null}
      </div>
      <pre className="max-h-72 overflow-auto border-t border-line bg-ink px-3 py-3 font-mono text-xs leading-relaxed text-text-dim whitespace-pre-wrap break-words">
        {body || (ok ? "(no output)" : trace.error || "(no output)")}
      </pre>
    </div>
  );
}
