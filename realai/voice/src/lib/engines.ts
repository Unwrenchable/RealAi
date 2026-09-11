export type EngineId = "kokoro" | "fish_s1" | "xtts" | "windows_sapi";

export type EngineDef = {
  id: EngineId;
  name: string;
  format: string;
  engineKey: "kokoro" | "fish_speech" | "xtts" | "windows_sapi";
  blurb: string;
  vramGb: number;
  trainVramGb: number | null;
  amd: string;
  clone: "none" | "zero-shot" | "finetune";
  modelRel: string;
  configRel?: string;
};

/** Local weight root — RealAI provider, not a cloud path. */
export const DEFAULT_MODELS_ROOT = "C:/models/checkpoints_lora";

export const STACK = {
  vulkanDir: "C:/llama-vulkan",
  llamaDir: "C:/llama",
  directmlDir: "C:/DirectML",
  vulkanUrl: "http://127.0.0.1:8080",
  hiveUrl: "http://127.0.0.1:8001",
  voiceLabUrl: "http://127.0.0.1:8890",
} as const;

export const KOKORO_VOICES = [
  { id: "af_heart", label: "Heart (US ♀)" },
  { id: "af_bella", label: "Bella (US ♀)" },
  { id: "af_nicole", label: "Nicole (US ♀)" },
  { id: "af_sarah", label: "Sarah (US ♀)" },
  { id: "am_adam", label: "Adam (US ♂)" },
  { id: "am_michael", label: "Michael (US ♂)" },
  { id: "am_fenrir", label: "Fenrir (US ♂)" },
  { id: "bf_emma", label: "Emma (GB ♀)" },
  { id: "bm_george", label: "George (GB ♂)" },
] as const;

export const ENGINES: EngineDef[] = [
  {
    id: "kokoro",
    name: "Kokoro",
    format: "PTH",
    engineKey: "kokoro",
    blurb: "Fast local neural TTS. Swap voice ids from the Kokoro pack — no training.",
    vramGb: 0.5,
    trainVramGb: null,
    amd: "HTTP :8880 or Windows SAPI fallback · DirectML-friendly",
    clone: "none",
    modelRel: "Kokoro/kokoro-v1_0.pth",
  },
  {
    id: "fish_s1",
    name: "Fish Speech S1",
    format: "PTH",
    engineKey: "fish_speech",
    blurb: "High-fidelity Fish Speech. Prefer for longer, expressive lines.",
    vramGb: 5,
    trainVramGb: null,
    amd: "HTTP :8081 · weights under fish_speech_s1",
    clone: "none",
    modelRel: "fish_speech_s1/text2semantic-sft-large-v1.1-4k.pth",
  },
  {
    id: "xtts",
    name: "XTTS v2",
    format: "PTH",
    engineKey: "xtts",
    blurb: "Best local clone path. Point speaker_wav at 2–5 min of clean WAV.",
    vramGb: 4,
    trainVramGb: 10,
    amd: "HTTP :8020 · ROCm / DirectML train path",
    clone: "zero-shot",
    modelRel: "xtts_v2/model.pth",
  },
  {
    id: "windows_sapi",
    name: "Windows SAPI",
    format: "System",
    engineKey: "windows_sapi",
    blurb: "Always-on offline fallback. No GPU. Hive uses this when neural HTTP is down.",
    vramGb: 0,
    trainVramGb: null,
    amd: "System.Speech · zero VRAM",
    clone: "none",
    modelRel: "",
  },
];

export const GPU = {
  name: "AMD Radeon (Vulkan)",
  vramGb: 12,
  notes: "Chat on C:/llama-vulkan :8080. Voice Lab on :8890. DirectML under C:/DirectML.",
};

export function joinRoot(root: string, rel: string) {
  if (!rel) return root.replaceAll("\\", "/").replace(/\/+$/, "");
  const base = root.replaceAll("\\", "/").replace(/\/+$/, "");
  return `${base}/${rel.replace(/^\/+/, "")}`;
}

export type TtsConfig = {
  provider: string;
  tts: Record<string, string | number>;
  stack: Record<string, string>;
};

export function buildTtsConfig(opts: {
  engineId: EngineId;
  rootPath: string;
  kokoroVoice: string;
  speakerWav: string;
}): TtsConfig {
  const engine = ENGINES.find((e) => e.id === opts.engineId) ?? ENGINES[0];
  const model_path = engine.modelRel
    ? joinRoot(opts.rootPath, engine.modelRel)
    : "";

  const stack = {
    vulkan_dir: STACK.vulkanDir,
    llama_dir: STACK.llamaDir,
    directml_dir: STACK.directmlDir,
    vulkan_base: STACK.vulkanUrl,
    hive: STACK.hiveUrl,
    voice_lab: STACK.voiceLabUrl,
  };

  if (engine.engineKey === "kokoro") {
    return {
      provider: "realai-voice",
      tts: {
        engine: "kokoro",
        model_path,
        voice: opts.kokoroVoice,
        voices_dir: joinRoot(opts.rootPath, "Kokoro/voices"),
      },
      stack,
    };
  }

  if (engine.engineKey === "fish_speech") {
    return {
      provider: "realai-voice",
      tts: {
        engine: "fish_speech",
        model_path,
        model_dir: joinRoot(opts.rootPath, "fish_speech_s1"),
      },
      stack,
    };
  }

  if (engine.engineKey === "windows_sapi") {
    return {
      provider: "realai-voice",
      tts: { engine: "windows_sapi" },
      stack,
    };
  }

  return {
    provider: "realai-voice",
    tts: {
      engine: "xtts",
      model_path,
      speaker_wav:
        opts.speakerWav.trim() ||
        joinRoot(opts.rootPath, "xtts_v2/samples/en_sample.wav"),
    },
    stack,
  };
}

export function buildTrainScript(opts: {
  rootPath: string;
  speakerName: string;
  batchSize: number;
  lr: string;
  epochs: number;
}) {
  const output = joinRoot(opts.rootPath, "xtts_custom");
  const data = joinRoot(opts.rootPath, `datasets/${slug(opts.speakerName)}_voice`);
  return `from TTS.api import TTS

# RealAI local XTTS fine-tune (AMD / DirectML box — no CUDA assumed)
tts = TTS("tts_models/multilingual/xtts_v2")

tts.train(
    output_path="${output}",
    data_path="${data}",
    batch_size=${opts.batchSize},
    lr=${opts.lr},
    epochs=${opts.epochs},
)
`;
}

export function buildCloneSnippet(opts: { speakerWav: string; text: string }) {
  const wav = opts.speakerWav.replaceAll("\\", "/");
  const text = opts.text.replaceAll('"', '\\"');
  return `from TTS.api import TTS

# RealAI zero-shot clone — local xtts_v2 weights
tts = TTS("tts_models/multilingual/xtts_v2")
tts.tts_to_file(
    text="${text}",
    speaker_wav="${wav}",
    language="en",
    file_path="out.wav",
)
`;
}

function slug(value: string) {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "") || "speaker"
  );
}
