import { ToolCard } from "./ToolCard";
import type { ChatMessage } from "@/lib/realai/types";

const CHIPS = [
  { label: "python --version", prompt: "python3 --version", mode: "run" as const },
  { label: "hello.py", prompt: "python3 scripts/hello.py", mode: "run" as const },
  { label: "sysinfo", prompt: "bash scripts/sysinfo.sh", mode: "run" as const },
  { label: "list hive", prompt: "list the files in the hive", mode: "ask" as const },
  { label: "who are you", prompt: "who are you?", mode: "ask" as const },
];

export function Feed({
  messages,
  pending,
  onChip,
}: {
  messages: ChatMessage[];
  pending: boolean;
  onChip: (prompt: string, mode: "ask" | "run") => void;
}) {
  if (!messages.length && !pending) {
    return (
      <div className="mx-auto max-w-xl px-2 pt-10 sm:pt-16">
        <h2 className="text-4xl font-semibold leading-none tracking-tight sm:text-5xl">
          Local hive.
          <br />
          <span className="text-acid">Commands run.</span>
        </h2>
        <p className="mt-4 max-w-prose text-sm leading-relaxed text-mute">
          RealAI Operator. Ask it to run a script, or switch to Run and hit the shell yourself.
          Output is captured from the real process — never invented.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {CHIPS.map((c) => (
            <button
              key={c.label}
              type="button"
              onClick={() => onChip(c.prompt, c.mode)}
              className="min-h-11 rounded-full bg-elevated px-3.5 text-xs text-text-dim shadow-[var(--shadow-border)] transition-colors duration-150 hover:text-text hover:shadow-[var(--shadow-border-hover)]"
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      {messages.map((m) => (
        <article key={m.id} className="flex flex-col gap-2">
          <div
            className={
              m.role === "assistant"
                ? "font-mono text-xs uppercase tracking-widest text-acid"
                : "font-mono text-xs uppercase tracking-widest text-mute"
            }
          >
            {m.role === "assistant" ? "RealAI" : "You"}
          </div>
          {m.traces?.length ? (
            <div className="flex flex-col gap-2">
              {m.traces.map((t) => (
                <ToolCard key={t.id} trace={t} />
              ))}
            </div>
          ) : null}
          {m.missedExec ? (
            <p className="rounded-md bg-panel px-3 py-2 text-xs text-hot shadow-[var(--shadow-border)]">
              No live exec this turn. Switch to Run to hit the real shell, or ask again with a
              concrete command.
            </p>
          ) : null}
          {m.content ? (
            <div
              className={
                m.role === "user"
                  ? "rounded-lg bg-user px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-[0_0_0_1px_rgba(214,255,63,0.18)]"
                  : "rounded-lg bg-elevated px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-[var(--shadow-border)]"
              }
            >
              {m.content}
            </div>
          ) : null}
        </article>
      ))}
      {pending ? (
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-acid">RealAI</div>
          <p className="shimmer mt-2 font-mono text-xs text-mute">running live…</p>
        </div>
      ) : null}
    </div>
  );
}
