"use client";

import { useState } from "react";
import { Check, Copy, Upload } from "lucide-react";
import { toast } from "sonner";
import { buildCloneSnippet, buildTrainScript, joinRoot } from "@/lib/engines";
import { cloneGrokVoice } from "@/lib/tts";
import { useLab } from "@/lib/store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

const CHECKS: { key: "duration" | "clean" | "wav" | "rate"; label: string; hint: string }[] = [
  { key: "duration", label: "2–5 minutes", hint: "Enough for XTTS. Grok clone caps at 2 min." },
  { key: "clean", label: "No background noise", hint: "Room tone only. No music, no fans." },
  { key: "wav", label: "WAV file", hint: "Uncompressed PCM." },
  { key: "rate", label: "44.1 or 48 kHz", hint: "Skip 16 kHz phone rips." },
];

export function CloneDeck() {
  const speakerName = useLab((s) => s.speakerName);
  const rootPath = useLab((s) => s.rootPath);
  const speakerRel = useLab((s) => s.speakerRel);
  const epochs = useLab((s) => s.epochs);
  const batchSize = useLab((s) => s.batchSize);
  const lr = useLab((s) => s.lr);
  const checks = useLab((s) => s.checks);
  const setSpeakerName = useLab((s) => s.setSpeakerName);
  const setEpochs = useLab((s) => s.setEpochs);
  const setBatchSize = useLab((s) => s.setBatchSize);
  const toggleCheck = useLab((s) => s.toggleCheck);
  const setCustomVoice = useLab((s) => s.setCustomVoice);

  const [busy, setBusy] = useState(false);
  const [fileLabel, setFileLabel] = useState<string | null>(null);

  const speakerWav = joinRoot(rootPath, speakerRel);
  const ready = Object.values(checks).filter(Boolean).length;
  const python = buildTrainScript({
    rootPath,
    speakerName,
    batchSize,
    lr,
    epochs,
  });
  const clonePy = buildCloneSnippet({
    speakerWav,
    text: "Voice check. This is the cloned speaker.",
  });

  async function copy(text: string, label: string) {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".wav") && file.type !== "audio/wav") {
      toast.error("Use a WAV clip.");
      return;
    }
    if (file.size > 4_000_000) {
      toast.error("Keep the Grok clip under 4 MB (mono WAV, under two minutes).");
      return;
    }
    setBusy(true);
    setFileLabel(file.name);
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = "";
      const chunk = 0x8000;
      for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
      }
      const audioBase64 = btoa(binary);
      const result = await cloneGrokVoice({
        data: { name: speakerName || "Custom", audioBase64, mime: "audio/wav" },
      });
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      setCustomVoice(result.voiceId, speakerName);
      toast.success("Clone ready — open Speak to hear it.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Clone failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <p className="text-sm text-muted">
        Two AMD-friendly paths. Kokoro is a voice pick, not a train. XTTS is the clone.
        Fish Speech stays inference-only on a 6700 XT.
      </p>

      <div className="grid gap-2">
        {CHECKS.map((item) => {
          const on = checks[item.key];
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => toggleCheck(item.key)}
              className={cn(
                "flex items-start gap-3 rounded-md p-3 text-left shadow-[var(--shadow-border)]",
                on ? "bg-raised" : "bg-bg",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-xs shadow-[var(--shadow-border)]",
                  on ? "bg-led text-bg" : "bg-raised text-transparent",
                )}
              >
                <Check className="size-3.5" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{item.label}</span>
                <span className="block text-xs text-muted">{item.hint}</span>
              </span>
            </button>
          );
        })}
        <p className="font-mono text-xs tabular-nums text-subtle">{ready}/4 ready</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-2">
          <Label htmlFor="speaker-name">Speaker</Label>
          <Input
            id="speaker-name"
            value={speakerName}
            onChange={(e) => setSpeakerName(e.target.value)}
          />
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <Label>Batch size</Label>
          <div className="flex gap-1.5">
            {[1, 2, 4].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setBatchSize(n)}
                className={cn(
                  "h-11 flex-1 rounded-md font-mono text-sm shadow-[var(--shadow-border)]",
                  batchSize === n ? "bg-accent text-accent-fg" : "bg-raised text-muted",
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>Epochs</Label>
          <span className="font-mono text-xs tabular-nums text-muted">{epochs}</span>
        </div>
        <Slider
          min={50}
          max={500}
          step={10}
          value={[epochs]}
          onValueChange={(v) => setEpochs(v[0] ?? 300)}
        />
        <p className="text-xs text-muted">lr {lr} · output models/tts/xtts_custom</p>
      </div>

      <div className="rounded-lg bg-bg p-4 shadow-[var(--shadow-border)]">
        <p className="font-mono text-xs tracking-widest text-subtle uppercase">
          Grok clone · ≤ 2 min WAV
        </p>
        <label className="mt-3 flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-md bg-raised px-4 py-5 text-center shadow-[var(--shadow-border)]">
          <Upload className="size-4 text-muted" />
          <span className="text-sm">
            {busy ? "Cloning…" : fileLabel ?? "Drop a reference WAV"}
          </span>
          <span className="text-xs text-muted">Creates a Grok custom voice for preview</span>
          <input
            type="file"
            accept="audio/wav,.wav"
            className="sr-only"
            disabled={busy}
            onChange={(e) => void onFile(e.target.files?.[0])}
          />
        </label>
      </div>

      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>XTTS train</Label>
          <button
            type="button"
            className="flex h-9 items-center gap-1.5 text-xs text-muted hover:text-fg"
            onClick={() => void copy(python, "Train script")}
          >
            <Copy className="size-3.5" />
            Copy
          </button>
        </div>
        <pre className="max-h-48 overflow-auto rounded-md bg-bg p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap text-fg shadow-[var(--shadow-border)]">
          {python}
        </pre>
      </div>

      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>Zero-shot clone</Label>
          <button
            type="button"
            className="flex h-9 items-center gap-1.5 text-xs text-muted hover:text-fg"
            onClick={() => void copy(clonePy, "Clone snippet")}
          >
            <Copy className="size-3.5" />
            Copy
          </button>
        </div>
        <pre className="max-h-40 overflow-auto rounded-md bg-bg p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap text-fg shadow-[var(--shadow-border)]">
          {clonePy}
        </pre>
      </div>
    </div>
  );
}
