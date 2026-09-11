import { useState } from "react";
import { Play } from "lucide-react";
import { cn } from "@/lib/utils";
import { ToolCard } from "./ToolCard";
import { execScript } from "@/lib/realai/actions";
import type { ExecTrace, ScriptLanguage } from "@/lib/realai/types";

const SAMPLES: Record<ScriptLanguage, string> = {
  python: `print("RealAI hive is live.")
print("This line was printed by python3 — not invented by a model.")
`,
  node: `console.log("RealAI hive is live.");
console.log("This line was printed by node — not invented by a model.");
`,
  bash: `echo "RealAI hive is live."
echo "This line was printed by bash — not invented by a model."
uname -srm
`,
};

export function ScriptPad({ onTrace }: { onTrace: (t: ExecTrace) => void }) {
  const [language, setLanguage] = useState<ScriptLanguage>("python");
  const [code, setCode] = useState(SAMPLES.python);
  const [filename, setFilename] = useState("scratch/job.py");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<ExecTrace | null>(null);

  const setLang = (lang: ScriptLanguage) => {
    setLanguage(lang);
    setCode(SAMPLES[lang]);
    setFilename(
      lang === "python" ? "scratch/job.py" : lang === "node" ? "scratch/job.js" : "scratch/job.sh",
    );
  };

  const run = async () => {
    if (busy || !code.trim()) return;
    setBusy(true);
    try {
      const res = await execScript({ data: { language, code, filename } });
      setLast(res.trace);
      onTrace(res.trace);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Script pad</h2>
        <p className="mt-1 text-sm text-mute">
          Written to the hive, then executed. The card below is real process output.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {(["python", "node", "bash"] as const).map((lang) => (
          <button
            key={lang}
            type="button"
            onClick={() => setLang(lang)}
            className={cn(
              "min-h-11 rounded-full px-3.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150",
              language === lang
                ? "bg-acid text-ink"
                : "bg-elevated text-mute shadow-[var(--shadow-border)] hover:text-text",
            )}
          >
            {lang}
          </button>
        ))}
        <input
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          className="min-h-11 min-w-0 flex-1 rounded-md bg-elevated px-3 font-mono text-xs text-text outline-none shadow-[var(--shadow-border)]"
          aria-label="Script filename"
        />
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="inline-flex min-h-11 items-center gap-2 rounded-md bg-acid px-4 text-sm font-semibold text-ink transition-transform duration-150 ease-out hover:brightness-105 active:scale-[0.96] disabled:opacity-40"
        >
          <Play className="size-3.5" />
          {busy ? "Running" : "Run script"}
        </button>
      </div>
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        spellCheck={false}
        className="min-h-56 rounded-lg bg-ink p-4 font-mono text-xs leading-relaxed text-text outline-none shadow-[var(--shadow-border)]"
      />
      {last ? <ToolCard trace={last} /> : null}
    </div>
  );
}
