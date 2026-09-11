import { useRef } from "react";
import { Play, Send } from "lucide-react";
import { cn } from "@/lib/utils";

export type ComposerMode = "ask" | "run";

export function Composer({
  value,
  mode,
  disabled,
  onChange,
  onMode,
  onSubmit,
}: {
  value: string;
  mode: ComposerMode;
  disabled: boolean;
  onChange: (v: string) => void;
  onMode: (m: ComposerMode) => void;
  onSubmit: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  return (
    <form
      className="mx-auto w-full max-w-3xl rounded-xl bg-panel p-2.5 pl-3.5 shadow-[var(--shadow-border),0_20px_60px_rgba(0,0,0,0.35)]"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <textarea
        id="hive-input"
        ref={ref}
        value={value}
        rows={2}
        disabled={disabled}
        placeholder={
          mode === "run"
            ? "Command — executed in the hive. Real stdout comes back."
            : "Talk to RealAI — it will exec, not invent."
        }
        className="w-full resize-none bg-transparent text-sm leading-relaxed text-text outline-none placeholder:text-mute disabled:opacity-50"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <div className="flex rounded-full bg-ink p-0.5 shadow-[var(--shadow-border)]">
          {(["ask", "run"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => onMode(m)}
              className={cn(
                "min-h-9 rounded-full px-3.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150",
                mode === m ? "bg-elevated text-acid" : "text-mute hover:text-text",
              )}
            >
              {m}
            </button>
          ))}
        </div>
        <span className="hidden font-mono text-xs text-mute sm:inline">
          {mode === "run" ? "no model · live shell" : "ENTER send · SHIFT+ENTER break"}
        </span>
        <button
          id="hive-send"
          type="submit"
          disabled={disabled || !value.trim()}
          className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-md bg-acid px-4 text-sm font-semibold text-ink transition-transform duration-150 ease-out hover:brightness-105 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {mode === "run" ? <Play className="size-3.5" /> : <Send className="size-3.5" />}
          {mode === "run" ? "Run" : "Send"}
        </button>
      </div>
    </form>
  );
}
