"use client";

import { cn } from "@/lib/utils";

export function Waveform({
  peaks,
  progress,
  className,
}: {
  peaks: number[];
  progress: number;
  className?: string;
}) {
  const bars = peaks.length > 8 ? peaks : Array.from({ length: 56 }, () => 0.1);
  const played = Math.max(0, Math.min(1, progress));

  return (
    <div
      className={cn("flex h-16 w-full min-w-0 items-center gap-px", className)}
      aria-hidden="true"
    >
      {bars.map((amp, i) => {
        const on = i / bars.length <= played;
        const scale = Math.max(0.08, Math.min(1, amp));
        return (
          <span
            key={i}
            className={cn(
              "h-full min-w-0 flex-1 origin-center rounded-full",
              on ? "bg-accent" : "bg-accent/25",
            )}
            style={{ transform: `scaleY(${scale})` }}
          />
        );
      })}
    </div>
  );
}

export async function extractPeaks(buffer: ArrayBuffer, bars = 56): Promise<number[]> {
  const Ctx =
    window.AudioContext ||
    (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return [];
  const ctx = new Ctx();
  try {
    await ctx.resume();
    const audio = await ctx.decodeAudioData(buffer.slice(0));
    const data = audio.getChannelData(0);
    const size = Math.floor(data.length / bars) || 1;
    const peaks: number[] = [];
    for (let i = 0; i < bars; i++) {
      let sum = 0;
      const start = i * size;
      for (let j = 0; j < size; j += 8) {
        sum += Math.abs(data[start + j] ?? 0);
      }
      peaks.push(Math.min(1, (sum / (size / 8)) * 3.2));
    }
    return peaks;
  } finally {
    await ctx.close().catch(() => undefined);
  }
}
