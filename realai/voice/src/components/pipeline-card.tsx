"use client";

import { useMemo, useState } from "react";
import { Check, Copy, Download } from "lucide-react";
import { toast } from "sonner";
import { buildTtsConfig, ENGINES, KOKORO_VOICES, joinRoot } from "@/lib/engines";
import { useLab } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function PipelineCard() {
  const engineId = useLab((s) => s.engineId);
  const rootPath = useLab((s) => s.rootPath);
  const kokoroVoice = useLab((s) => s.kokoroVoice);
  const speakerRel = useLab((s) => s.speakerRel);
  const setRootPath = useLab((s) => s.setRootPath);
  const setKokoroVoice = useLab((s) => s.setKokoroVoice);
  const setSpeakerRel = useLab((s) => s.setSpeakerRel);
  const [copied, setCopied] = useState(false);

  const speakerWav = joinRoot(rootPath, speakerRel);
  const config = useMemo(
    () => buildTtsConfig({ engineId, rootPath, kokoroVoice, speakerWav }),
    [engineId, rootPath, kokoroVoice, speakerWav],
  );
  const json = JSON.stringify(config, null, 2);
  const engine = ENGINES.find((e) => e.id === engineId) ?? ENGINES[0];

  async function copy() {
    await navigator.clipboard.writeText(json);
    setCopied(true);
    toast.success("Pipeline JSON copied");
    window.setTimeout(() => setCopied(false), 1400);
  }

  function download() {
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tts.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="flex min-w-0 flex-col gap-4 rounded-xl bg-surface p-4 shadow-[var(--shadow-border)] lg:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-widest text-subtle uppercase">Pipeline</p>
          <h2 className="font-display text-lg font-semibold tracking-tight">Active config</h2>
        </div>
        <Badge tone="led">{engine.engineKey}</Badge>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="root">Models root (checkpoints_lora)</Label>
        <Input
          id="root"
          value={rootPath}
          onChange={(e) => setRootPath(e.target.value)}
          spellCheck={false}
        />
      </div>

      {engine.id === "kokoro" ? (
        <div className="flex flex-col gap-2">
          <Label>Kokoro voice</Label>
          <div className="flex flex-wrap gap-1.5">
            {KOKORO_VOICES.map((voice) => (
              <button
                key={voice.id}
                type="button"
                onClick={() => setKokoroVoice(voice.id)}
                className={cn(
                  "h-9 rounded-sm px-2.5 font-mono text-xs shadow-[var(--shadow-border)]",
                  kokoroVoice === voice.id ? "bg-accent text-accent-fg" : "bg-raised text-muted",
                )}
              >
                {voice.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {engine.id === "xtts" ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="speaker">Speaker WAV (relative)</Label>
          <Input
            id="speaker"
            value={speakerRel}
            onChange={(e) => setSpeakerRel(e.target.value)}
            spellCheck={false}
          />
        </div>
      ) : null}

      <pre className="max-h-64 overflow-auto rounded-md bg-bg p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap text-fg shadow-[var(--shadow-border)]">
        {json}
      </pre>

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={() => void copy()}>
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copied ? "Copied" : "Copy JSON"}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={download}>
          <Download className="size-4" />
          Download
        </Button>
      </div>
      <p className="text-xs leading-snug text-muted">
        RealAI reads this block. Change the engine and model path — that is the whole swap.
      </p>
    </section>
  );
}
