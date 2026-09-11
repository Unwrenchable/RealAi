import { createServerFn } from "@tanstack/react-start";
import { spawn } from "node:child_process";
import { MAX_TTS_CHARS } from "@/lib/voices";

const VOICE_ID_RE = /^[a-z0-9_-]{2,40}$/i;
const VOICE_LAB =
  process.env.REALAI_VOICE_LAB_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8890";

type SpeakOk = { ok: true; audioBase64: string; mime: string; backend?: string };
type SpeakErr = { ok: false; error: string };
type SpeakResult = SpeakOk | SpeakErr;

async function speakViaLab(
  text: string,
  voiceId: string,
  backend?: string,
): Promise<SpeakResult | null> {
  try {
    const res = await fetch(`${VOICE_LAB}/v1/audio/speech?format=json`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        input: text,
        voice: voiceId,
        backend: backend || undefined,
        response_format: "json",
      }),
      signal: AbortSignal.timeout(90_000),
    });
    if (!res.ok) return null;
    const body = (await res.json()) as {
      ok?: boolean;
      audio_b64?: string;
      backend?: string;
      error?: string;
    };
    if (!body.ok || !body.audio_b64) return null;
    return {
      ok: true,
      audioBase64: body.audio_b64,
      mime: "audio/wav",
      backend: body.backend,
    };
  } catch {
    return null;
  }
}

function speakViaPython(
  text: string,
  voiceId: string,
  backend?: string,
): Promise<SpeakResult> {
  const payload = JSON.stringify({
    text,
    voice: voiceId,
    backend: backend || null,
  });
  const code = `
import json, sys
from realai.voice.provider import get_voice_provider
req = json.loads(sys.argv[1])
out = get_voice_provider().speak(
    req.get("text") or "",
    voice=req.get("voice"),
    backend=req.get("backend"),
    prepare=True,
    as_base64=True,
)
print(json.dumps(out))
`.trim();

  return new Promise((resolve) => {
    const child = spawn("python", ["-c", code, payload], {
      env: { ...process.env },
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    child.on("error", (err) => {
      resolve({ ok: false, error: `Python voice failed: ${err.message}` });
    });
    child.on("close", (code) => {
      try {
        const line = stdout.trim().split(/\r?\n/).filter(Boolean).pop() || "";
        const body = JSON.parse(line) as {
          ok?: boolean;
          audio_b64?: string;
          backend?: string;
          error?: string;
        };
        if (body.ok && body.audio_b64) {
          resolve({
            ok: true,
            audioBase64: body.audio_b64,
            mime: "audio/wav",
            backend: body.backend,
          });
          return;
        }
        resolve({
          ok: false,
          error: body.error || stderr.slice(0, 240) || `voice exit ${code}`,
        });
      } catch {
        resolve({
          ok: false,
          error:
            stderr.slice(0, 240) ||
            "Local RealAI voice provider returned no audio.",
        });
      }
    });
  });
}

export const synthesizeSpeech = createServerFn({ method: "POST" })
  .validator(
    (input: { text: string; voiceId: string; backend?: string }) => {
      const text = String(input.text ?? "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, MAX_TTS_CHARS);
      const voiceId = String(input.voiceId ?? "").trim();
      const backend = String(input.backend ?? "").trim() || undefined;
      if (!text) throw new Error("Enter something to speak.");
      if (!VOICE_ID_RE.test(voiceId) && voiceId !== "sapi") {
        throw new Error("Unknown voice.");
      }
      return { text, voiceId, backend };
    },
  )
  .handler(async ({ data }): Promise<SpeakResult> => {
    const viaLab = await speakViaLab(data.text, data.voiceId, data.backend);
    if (viaLab) return viaLab;
    return speakViaPython(data.text, data.voiceId, data.backend);
  });

export const voiceLabHealth = createServerFn({ method: "GET" }).handler(
  async () => {
    try {
      const res = await fetch(`${VOICE_LAB}/v1/voice/health`, {
        signal: AbortSignal.timeout(4000),
      });
      if (res.ok) return (await res.json()) as Record<string, unknown>;
    } catch {
      /* fall through to python */
    }
    return new Promise<Record<string, unknown>>((resolve) => {
      const code = `import json; from realai.voice.provider import get_voice_provider; print(json.dumps(get_voice_provider().health()))`;
      const child = spawn("python", ["-c", code], {
        env: { ...process.env },
        windowsHide: true,
      });
      let stdout = "";
      child.stdout.on("data", (c) => {
        stdout += String(c);
      });
      child.on("error", () =>
        resolve({ ok: false, error: "Voice provider unreachable" }),
      );
      child.on("close", () => {
        try {
          const line = stdout.trim().split(/\r?\n/).filter(Boolean).pop() || "{}";
          resolve(JSON.parse(line) as Record<string, unknown>);
        } catch {
          resolve({ ok: false, error: "Voice provider unreachable" });
        }
      });
    });
  },
);

/** Local XTTS clone is zero-shot via speaker_wav — save clip path in lab state. */
export const registerLocalClone = createServerFn({ method: "POST" })
  .validator((input: { name: string; speakerWav: string }) => {
    const name = String(input.name ?? "")
      .trim()
      .slice(0, 48);
    const speakerWav = String(input.speakerWav ?? "").trim();
    if (name.length < 2) throw new Error("Name the voice.");
    if (speakerWav.length < 4) throw new Error("Set a speaker WAV path.");
    return { name, speakerWav };
  })
  .handler(async ({ data }) => {
    return {
      ok: true as const,
      voiceId: `xtts:${data.name}`,
      speakerWav: data.speakerWav,
      note: "Local XTTS zero-shot — set REALAI_XTTS_SPEAKER to this WAV for hive speak.",
    };
  });
