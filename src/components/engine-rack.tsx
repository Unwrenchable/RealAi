"use client";

import { ENGINES, GPU } from "@/lib/engines";
import { useLab } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Meter } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export function EngineRack() {
  const engineId = useLab((s) => s.engineId);
  const setEngine = useLab((s) => s.setEngine);
  const active = ENGINES.find((e) => e.id === engineId) ?? ENGINES[0];
  const used = active.vramGb;

  return (
    <aside className="flex min-w-0 flex-col gap-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-widest text-subtle uppercase">Rack</p>
          <h2 className="font-display text-lg font-semibold tracking-tight">Engines</h2>
        </div>
        <Badge>{active.format}</Badge>
      </div>

      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-1">
        {ENGINES.map((engine) => {
          const on = engine.id === engineId;
          return (
            <li key={engine.id} className="min-w-0">
              <button
                type="button"
                onClick={() => setEngine(engine.id)}
                className={cn(
                  "flex w-full flex-col gap-2 rounded-lg p-3 text-left shadow-[var(--shadow-border)] transition-[box-shadow,background-color] duration-150 ease-[var(--ease-smooth)]",
                  on
                    ? "bg-raised shadow-[var(--shadow-border-hover)]"
                    : "bg-surface hover:shadow-[var(--shadow-border-hover)]",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      className={cn("size-1.5 shrink-0 rounded-full", on ? "bg-led" : "bg-border")}
                      aria-hidden
                    />
                    <span className="truncate font-medium">{engine.name}</span>
                  </span>
                  <span className="shrink-0 font-mono text-xs tabular-nums text-muted">
                    {engine.vramGb} GB
                  </span>
                </div>
                <p className="text-xs leading-snug text-muted">{engine.blurb}</p>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="rounded-lg bg-surface p-4 shadow-[var(--shadow-border)]">
        <div className="flex items-center justify-between gap-2">
          <p className="font-mono text-xs tracking-widest text-subtle uppercase">GPU</p>
          <span className="font-mono text-xs tabular-nums text-muted">
            {used}/{GPU.vramGb} GB
          </span>
        </div>
        <p className="mt-1 text-sm font-medium">{GPU.name}</p>
        <Meter className="mt-3" value={used} max={GPU.vramGb} />
        <p className="mt-2 text-xs leading-snug text-muted">{active.amd}</p>
        {active.trainVramGb ? (
          <p className="mt-1 text-xs text-muted">
            Fine-tune ~{active.trainVramGb} GB with batch 4. {GPU.notes}
          </p>
        ) : null}
      </div>
    </aside>
  );
}
