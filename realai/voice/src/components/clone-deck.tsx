"use client";

import { useState } from "react";
import { Check, Copy, Upload } from "lucide-react";
import { toast } from "sonner";
import { buildCloneSnippet, buildTrainScript, joinRoot } from "@/lib/engines";
import { registerLocalClone } from "@/lib/tts";
import { useLab } from "@/lib/store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

const CHECKS: {
  key: "duration" | "clean" | "wav" | "rate";
  label: string;
  hint: string;
}[] = [
  {
    key: "duration",
    label: "2–5 minutes",
    hint: "Enough for XTTS zero-shot or a short fine-tune.",
  },
  {
    key: "clean",
    label: "No background noise",
    hint: "Room tone only. No music, no fans.",
  },
  { key: "wav", label: "WAV file", hint: "Uncompressed PCM." },
  {
    key: "rate",
    label: "44.1 or 48 kHz",
    hint: "Skip 16 kHz phone rips.",
  },
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
  const setSpeakerRel = useLab((s) => s.setSpeakerRel);
  const setEpochs = useLab((s) => s.setEpochs);
  const setBatchSize = useLab((s) => s.setBatchSize);
  const setLr = useLab((s) => s.setLr);
  const toggleCheck = useLab((s) => s.toggleCheck);

  const [busy, setBusy] = useState(false);
  const [fileLabel, setFileLabel] = useState<string | null>(null);
  const [registered, setRegistered] = useState<string | null>(null);

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
    text: "Voice check. This is the cloned RealAI speaker.",
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
    if (file.size > 40_000_000) {
      toast.error("Keep the reference WAV under ~40 MB.");
      return;
    }
    setBusy(true);
    setFileLabel(file.name);
    try {
      // Browser can't write into checkpoints_lora — register the intended path.
      const rel = `voices/${(speakerName || "custom").toLowerCase().replace(/[^a-z0-9]+/g, "_")}.wav`;
      setSpeakerRel(rel);
      const path = joinRoot(rootPath, rel);
      const result = await registerLocalClone({
        data: { name: speakerName || "Custom", speakerWav: path },
      });
      if (!result.ok) {
        toast.error("Could not register clone path.");
        return;
      }
      setRegistered(result.voiceId);
      toast.success(
        `Registered ${result.voiceId}. Save the WAV to ${path} and set REALAI_XTTS_SPEAKER.`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Clone register failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div>
        <p className="font-mono text-xs tracking-widest text-subtle uppercase">
          Local clone
        </p>
        <h3 className="font-display text-lg font-semibold tracking-tight">
          XTTS zero-shot
        </h3>
        <p className="mt-1 text-sm text-muted">
          No cloud voices. Drop a clean WAV under{" "}
          <span className="font-mono text-xs">{rootPath}</span>, then point
          hive at it with <span className="font-mono text-xs">REALAI_XTTS_SPEAKER</span>.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="speaker">Speaker name</Label>
          <Input
            id="speaker"
            value={speakerName}
            onChange={(e) => setSpeakerName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Reference WAV</Label>
          <label className="flex h-10 cursor-pointer items-center gap-2 rounded-md bg-raised px-3 text-sm shadow-[var(--shadow-border)]">
            <Upload className="size-4 text-muted" />
            <span className="truncate text-muted">
              {fileLabel || "Choose WAV…"}
            </span>
            <input
              type="file"
              accept="audio/wav,.wav"
              className="hidden"
              disabled={busy}
              onChange={(e) => void onFile(e.target.files?.[0])}
            />
          </label>
        </div>
      </div>

      <p className="font-mono text-xs break-all text-muted">{speakerWav}</p>
      {registered ? (
        <p className="text-sm text-led">Registered: {registered}</p>
      ) : null}

      <ul className="grid gap-2 sm:grid-cols-2">
        {CHECKS.map((c) => (
          <li key={c.key}>
            <button
              type="button"
              onClick={() => toggleCheck(c.key)}
              className={cn(
                "flex w-full items-start gap-2 rounded-lg p-3 text-left shadow-[var(--shadow-border)]",
                checks[c.key] ? "bg-raised" : "bg-surface",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-sm",
                  checks[c.key] ? "bg-led text-bg" : "bg-border",
                )}
              >
                {checks[c.key] ? <Check className="size-3" /> : null}
              </span>
              <span>
                <span className="block text-sm font-medium">{c.label}</span>
                <span className="text-xs text-muted">{c.hint}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className="font-mono text-xs text-subtle">{ready}/4 dataset checks</p>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>Fine-tune epochs</Label>
          <span className="font-mono text-xs tabular-nums">{epochs}</span>
        </div>
        <Slider
          value={[epochs]}
          min={50}
          max={600}
          step={10}
          onValueChange={([v]) => setEpochs(v)}
        />
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>Batch size</Label>
          <span className="font-mono text-xs tabular-nums">{batchSize}</span>
        </div>
        <Slider
          value={[batchSize]}
          min={1}
          max={8}
          step={1}
          onValueChange={([v]) => setBatchSize(v)}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="lr">Learning rate</Label>
        <Input id="lr" value={lr} onChange={(e) => setLr(e.target.value)} />
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex h-9 items-center gap-1.5 rounded-md bg-raised px-3 text-xs shadow-[var(--shadow-border)]"
          onClick={() => void copy(clonePy, "Zero-shot snippet")}
        >
          <Copy className="size-3.5" /> Zero-shot snippet
        </button>
        <button
          type="button"
          className="inline-flex h-9 items-center gap-1.5 rounded-md bg-raised px-3 text-xs shadow-[var(--shadow-border)]"
          onClick={() => void copy(python, "Train script")}
        >
          <Copy className="size-3.5" /> Train script
        </button>
      </div>
    </div>
  );
}
