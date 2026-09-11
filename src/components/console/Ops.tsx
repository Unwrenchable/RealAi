import { useState } from "react";
import { File, Folder } from "lucide-react";
import { ToolCard } from "./ToolCard";
import type { ExecTrace, HiveFile, HiveStatus } from "@/lib/realai/types";

function Meter({ pct, ice }: { pct: number; ice?: boolean }) {
  return (
    <div className="mt-2 h-0.5 overflow-hidden rounded-full bg-elevated">
      <i
        className={ice ? "block h-full bg-ice" : "block h-full bg-acid"}
        style={{ width: `${Math.max(6, Math.min(100, pct))}%` }}
      />
    </div>
  );
}

export function Ops({
  status,
  log,
  files,
  onOpenFile,
}: {
  status: HiveStatus | null;
  log: ExecTrace[];
  files: HiveFile[];
  onOpenFile: (path: string) => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const last = log[0];

  return (
    <aside className="hidden min-h-0 flex-col overflow-auto border-l border-line bg-rail xl:flex">
      <h3 className="px-4 pt-4 pb-2 font-mono text-xs uppercase tracking-widest text-mute">Ops</h3>

      <div className="mx-3 mb-2 rounded-md bg-panel p-3 shadow-[var(--shadow-border)]">
        <b className="block text-xs font-medium">Provider</b>
        <span className="text-xs text-mute">RealAI local orch :8001 — no xAI</span>
      </div>
      <div className="mx-3 mb-2 rounded-md bg-panel p-3 shadow-[var(--shadow-border)]">
        <b className="block text-xs font-medium">Exec</b>
        <span className="text-xs text-mute">live process · fail closed</span>
        <Meter pct={status?.ok ? 78 : 12} />
      </div>
      <div className="mx-3 mb-2 rounded-md bg-panel p-3 shadow-[var(--shadow-border)]">
        <b className="block text-xs font-medium">Runtime</b>
        <span className="font-mono text-xs text-mute">{status?.python ?? "…"}</span>
        <span className="mt-1 block font-mono text-xs text-mute">{status?.node ?? "…"}</span>
        <Meter pct={62} ice />
      </div>
      <div className="mx-3 mb-3 rounded-md bg-panel p-3 shadow-[var(--shadow-border)]">
        <b className="block text-xs font-medium">Rule</b>
        <span className="text-xs text-mute">Never invent stdout. Quote the process.</span>
      </div>

      <h3 className="px-4 pt-2 pb-2 font-mono text-xs uppercase tracking-widest text-mute">Last run</h3>
      <div className="px-3 pb-3">
        {last ? (
          <ToolCard trace={last} />
        ) : (
          <p className="rounded-md bg-panel px-3 py-3 text-xs text-mute shadow-[var(--shadow-border)]">
            No live exec yet. Run a command or a script.
          </p>
        )}
      </div>

      <h3 className="px-4 pt-1 pb-2 font-mono text-xs uppercase tracking-widest text-mute">Hive files</h3>
      <div className="px-3 pb-4">
        <ul className="rounded-md bg-panel shadow-[var(--shadow-border)]">
          {files.length === 0 ? (
            <li className="px-3 py-3 text-xs text-mute">empty</li>
          ) : (
            files.map((f) => (
              <li key={f.path} className="border-b border-line last:border-0">
                <button
                  type="button"
                  onClick={() => {
                    if (f.type === "dir") {
                      setOpen(open === f.path ? null : f.path);
                      onOpenFile(f.path);
                    } else {
                      onOpenFile(f.path);
                    }
                  }}
                  className="flex min-h-11 w-full items-center gap-2 px-3 text-left text-xs"
                >
                  {f.type === "dir" ? (
                    <Folder className="size-3.5 text-ice" />
                  ) : (
                    <File className="size-3.5 text-mute" />
                  )}
                  <span className="truncate font-mono">{f.name}</span>
                  {f.type === "file" ? (
                    <span className="ml-auto font-mono tabular-nums text-mute">{f.size}</span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </aside>
  );
}
