import { createServerFn } from "@tanstack/react-start";
import { MAX_TTS_CHARS } from "@/lib/voices";

const VOICE_ID_RE = /^[a-z0-9_-]{2,40}$/i;

export const synthesizeSpeech = createServerFn({ method: "POST" })
  .validator((input: { text: string; voiceId: string }) => {
    const text = String(input.text ?? "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, MAX_TTS_CHARS);
    const voiceId = String(input.voiceId ?? "").trim();
    if (!text) throw new Error("Enter something to speak.");
    if (!VOICE_ID_RE.test(voiceId)) throw new Error("Unknown voice.");
    return { text, voiceId };
  })
  .handler(async ({ data }) => {
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) {
      return { ok: false as const, error: "Voice preview is unavailable right now." };
    }

    const res = await fetch("https://api.x.ai/v1/tts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        text: data.text,
        voice_id: data.voiceId,
        language: "en",
      }),
    });

    if (!res.ok) {
      return { ok: false as const, error: `Voice preview failed (${res.status}).` };
    }

    const buf = Buffer.from(await res.arrayBuffer());
    const mime = res.headers.get("content-type") || "audio/mpeg";
    return { ok: true as const, audioBase64: buf.toString("base64"), mime };
  });

export const cloneGrokVoice = createServerFn({ method: "POST" })
  .validator((input: { name: string; audioBase64: string; mime: string }) => {
    const name = String(input.name ?? "")
      .trim()
      .slice(0, 48);
    const audioBase64 = String(input.audioBase64 ?? "");
    const mime = String(input.mime ?? "audio/wav");
    if (name.length < 2) throw new Error("Name the voice.");
    if (audioBase64.length < 100) throw new Error("Audio clip is empty.");
    if (audioBase64.length > 5_500_000) {
      throw new Error("Clip is too large. Keep a clean WAV under two minutes.");
    }
    return { name, audioBase64, mime };
  })
  .handler(async ({ data }) => {
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) {
      return { ok: false as const, error: "Voice cloning is unavailable right now." };
    }

    const bytes = Uint8Array.from(Buffer.from(data.audioBase64, "base64"));
    const form = new FormData();
    form.append("name", data.name);
    form.append("language", "en");
    form.append(
      "file",
      new Blob([bytes], { type: data.mime || "audio/wav" }),
      "reference.wav",
    );

    const res = await fetch("https://api.x.ai/v1/custom-voices", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    });

    if (!res.ok) {
      return {
        ok: false as const,
        error: `Clone failed (${res.status}). Use a clean WAV under two minutes.`,
      };
    }

    const body = (await res.json()) as { voice_id?: string };
    if (!body.voice_id) {
      return { ok: false as const, error: "Clone returned no voice id." };
    }
    return { ok: true as const, voiceId: body.voice_id };
  });
