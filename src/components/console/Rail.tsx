import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HiveStatus, Thread } from "@/lib/realai/types";

export function Rail({
  threads,
  activeId,
  status,
  onNew,
  onSelect,
  className,
}: {
  threads: Thread[];
  activeId: string;
  status: HiveStatus | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  className?: string;
}) {
  const live = status?.ok;
  return (
    <aside className={cn("flex min-h-0 flex-col bg-rail", className)}>
      <div className="flex items-center gap-3 px-4 py-4">
        <div className="grid size-9 place-items-center rounded-md bg-acid font-mono text-sm font-semibold text-ink shadow-[0_0_24px_rgba(214,255,63,0.35)]">
          R
        </div>
        <div>
          <h1 className="text-sm font-semibold uppercase tracking-widest">RealAI</h1>
          <p className="font-mono text-xs text-mute">local hive // bot</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onNew}
        className="mx-3 mb-3 flex min-h-11 items-center justify-center gap-2 rounded-md bg-acid px-3 text-sm font-semibold text-ink transition-transform duration-150 ease-out hover:brightness-105 active:scale-[0.96]"
      >
        <Plus className="size-4" />
        New thread
      </button>

      <div className="px-4 pb-2 font-mono text-xs uppercase tracking-widest text-mute">Threads</div>
      <div className="min-h-0 flex-1 overflow-auto px-2 pb-3">
        {threads.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(t.id)}
            className={cn(
              "mb-1 w-full rounded-md px-3 py-2.5 text-left text-sm text-text-dim transition-colors duration-150",
              t.id === activeId
                ? "bg-elevated text-text shadow-[0_0_0_1px_rgba(214,255,63,0.25)]"
                : "hover:bg-elevated hover:text-text",
            )}
          >
            <span className="block truncate">{t.title}</span>
            <span className="mt-0.5 block font-mono text-xs text-mute">
              {t.messages.length} turn{t.messages.length === 1 ? "" : "s"}
            </span>
          </button>
        ))}
      </div>

      <div className="m-3 rounded-md bg-panel p-3 shadow-[var(--shadow-border)]">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-2">
            <span
              className={cn(
                "inline-block size-1.5 rounded-full",
                live ? "live-dot bg-acid shadow-[0_0_8px_var(--color-acid)]" : "bg-hot shadow-[0_0_8px_var(--color-hot)]",
              )}
            />
            Local node
          </span>
          <span className="font-mono text-xs text-ice">{live ? "LIVE" : status ? "DOWN" : "SCAN"}</span>
        </div>
        <div className="mt-2 flex justify-between font-mono text-xs text-mute">
          <span>provider</span>
          <span>RealAI</span>
        </div>
      </div>
    </aside>
  );
}
