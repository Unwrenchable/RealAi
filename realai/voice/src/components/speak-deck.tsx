"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { toast } from "sonner";
import { synthesizeSpeech } from "@/lib/tts";
import { LAB_VOICES, MAX_TTS_CHARS, SAMPLE_LINES } from "@/lib/voices";
import { useLab } from "@/lib/store";
import { ENGINES } from "@/lib/engines";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Waveform, extractPeaks } from "@/components/waveform";
import { cn } from "@/lib/utils";

export function SpeakDeck() {
  const kokoroVoice = useLab((s) => s.kokoroVoice);
  const engineId = useLab((s) => s.engineId);
  const lastLine = useLab((s) => s.lastLine);
  const setKokoroVoice = useLab((s) => s.setKokoroVoice);
  const setLastLine = useLab((s) => s.setLastLine);

  const [text, setText] = useState(lastLine || SAMPLE_LINES[0]);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [peaks, setPeaks] = useState<number[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [backendUsed, setBackendUsed] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);

  const engine = ENGINES.find((e) => e.id === engineId) ?? ENGINES[0];
  const backend =
    engine.engineKey === "fish_speech"
      ? "fish"
      : engine.engineKey === "windows_sapi"
        ? "windows_sapi"
        : engine.engineKey;

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  function bindAudio(audio: HTMLAudioElement) {
    audio.ontimeupdate = () => {
      if (!audio.duration) return;
      setProgress(audio.currentTime / audio.duration);
    };
    audio.onended = () => {
      setPlaying(false);
      setProgress(1);
    };
  }

  async function speak() {
    const line = text.trim();
    if (!line) {
      toast.error("Write a line first.");
      return;
    }
    setBusy(true);
    setPlaying(false);
    setStatus(null);
    try {
      const result = await synthesizeSpeech({
        data: { text: line, voiceId: kokoroVoice, backend },
      });
      if (!result.ok) {
        setStatus(result.error);
        toast.error(result.error);
        return;
      }
      const bytes = Uint8Array.from(atob(result.audioBase64), (c) =>
        c.charCodeAt(0),
      );
      const blob = new Blob([bytes], { type: result.mime || "audio/wav" });
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      const url = URL.createObjectURL(blob);
      urlRef.current = url;
      const audio = audioRef.current ?? new Audio();
      audioRef.current = audio;
      bindAudio(audio);
      audio.src = url;
      await audio.play();
      setPlaying(true);
      setBackendUsed(result.backend || backend);
      setLastLine(line);
      void extractPeaks(await blob.arrayBuffer())
        .then(setPeaks)
        .catch(() => setPeaks([]));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not speak.";
      setStatus(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  function toggle() {
    const audio = audioRef.current;
    if (!audio?.src) {
      void speak();
      return;
    }
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      void audio.play().then(() => setPlaying(true));
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="line">Line</Label>
          <span className="font-mono text-xs tabular-nums text-subtle">
            {text.length}/{MAX_TTS_CHARS}
          </span>
        </div>
        <Textarea
          id="line"
          value={text}
          maxLength={MAX_TTS_CHARS}
          onChange={(e) => setText(e.target.value)}
          placeholder="What should the hive bot say?"
        />
        <div className="flex flex-wrap gap-1.5">
          {SAMPLE_LINES.map((line, i) => (
            <button
              key={line}
              type="button"
              onClick={() => setText(line)}
              className="h-9 max-w-full truncate rounded-sm bg-raised px-2.5 text-xs text-muted shadow-[var(--shadow-border)] hover:text-fg"
            >
              Sample {i + 1}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label>Kokoro voice (local pack)</Label>
        <div className="flex flex-wrap gap-1.5">
          {LAB_VOICES.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setKokoroVoice(v.id)}
              className={cn(
                "h-9 rounded-sm px-2.5 text-xs shadow-[var(--shadow-border)]",
                kokoroVoice === v.id
                  ? "bg-accent text-accent-fg"
                  : "bg-raised text-muted hover:text-fg",
              )}
              title={v.tone}
            >
              {v.name}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted">
          Speaks through RealAI Voice provider · engine rack selects backend ·
          Windows SAPI if neural HTTP is down.
        </p>
        {backendUsed ? (
          <p className="font-mono text-xs text-led">last backend: {backendUsed}</p>
        ) : null}
      </div>

      <div className="min-w-0 overflow-hidden rounded-lg bg-bg p-3 shadow-[var(--shadow-border)]">
        <Waveform peaks={peaks} progress={progress} />
      </div>

      {status ? <p className="text-sm text-danger">{status}</p> : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          onClick={() => void speak()}
          disabled={busy}
          size="lg"
          className="min-w-36"
        >
          {busy ? "Rendering…" : "Speak"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="lg"
          onClick={toggle}
          disabled={busy}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause className="size-4" />
          ) : (
            <Play className="ml-0.5 size-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
