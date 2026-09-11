export type EngineId = "kokoro" | "fish_s1" | "fish_s2" | "xtts";

export type EngineDef = {
  id: EngineId;
  name: string;
  format: string;
  engineKey: "kokoro" | "fish_speech" | "xtts";
  blurb: string;
  vramGb: number;
  trainVramGb: number | null;
  amd: string;
  clone: "none" | "zero-shot" | "finetune";
  modelRel: string;
  configRel?: string;
};

export const KOKORO_VOICES = [
  { id: "en_US_male", label: "US male" },
  { id: "en_US_female", label: "US female" },
  { id: "en_GB_male", label: "GB male" },
  { id: "en_GB_female", label: "GB female" },
] as const;

export const ENGINES: EngineDef[] = [
  {
    id: "kokoro",
    name: "Kokoro",
    format: "ONNX",
    engineKey: "kokoro",
    blurb: "Light, fast, DirectML-friendly. Swap the voice id — no training.",
    vramGb: 0.5,
    trainVramGb: null,
    amd: "ONNX Runtime + DirectML",
    clone: "none",
    modelRel: "models/tts/kokoro/kokoro-v1.onnx",
  },
  {
    id: "fish_s1",
    name: "Fish Speech S1",
    format: "Safetensors",
    engineKey: "fish_speech",
    blurb: "High-fidelity inference. Training is CUDA-first — keep this for playback.",
    vramGb: 5,
    trainVramGb: null,
    amd: "Inference on ROCm / DirectML",
    clone: "none",
    modelRel: "models/tts/fish_s1/model.safetensors",
    configRel: "models/tts/fish_s1/config.json",
  },
  {
    id: "fish_s2",
    name: "Fish Speech S2",
    format: "Safetensors",
    engineKey: "fish_speech",
    blurb: "Newer Fish checkpoint. Same swap rule: engine + model path.",
    vramGb: 7,
    trainVramGb: null,
    amd: "Inference on ROCm / DirectML",
    clone: "none",
    modelRel: "models/tts/fish_s2/model.safetensors",
    configRel: "models/tts/fish_s2/config.json",
  },
  {
    id: "xtts",
    name: "XTTS v2",
    format: "PTH",
    engineKey: "xtts",
    blurb: "Best AMD clone. 2–5 min of clean WAV, then speaker_wav or a short fine-tune.",
    vramGb: 4,
    trainVramGb: 10,
    amd: "ROCm / DirectML — best clone path",
    clone: "finetune",
    modelRel: "models/tts/xtts_v2/model.pth",
  },
];

export const GPU = {
  name: "Radeon RX 6700 XT",
  vramGb: 12,
  notes: "Batch 4 fits. If VRAM spikes during XTTS train, drop to batch 2.",
};

export function joinRoot(root: string, rel: string) {
  const base = root.replaceAll("\\", "/").replace(/\/+$/, "");
  return `${base}/${rel.replace(/^\/+/, "")}`;
}

export type TtsConfig = {
  tts: Record<string, string | number>;
};

export function buildTtsConfig(opts: {
  engineId: EngineId;
  rootPath: string;
  kokoroVoice: string;
  speakerWav: string;
}): TtsConfig {
  const engine = ENGINES.find((e) => e.id === opts.engineId) ?? ENGINES[0];
  const model_path = joinRoot(opts.rootPath, engine.modelRel);

  if (engine.engineKey === "kokoro") {
    return {
      tts: {
        engine: "kokoro",
        model_path,
        voice: opts.kokoroVoice,
      },
    };
  }

  if (engine.engineKey === "fish_speech") {
    return {
      tts: {
        engine: "fish_speech",
        model_path,
        config: joinRoot(opts.rootPath, engine.configRel ?? ""),
      },
    };
  }

  return {
    tts: {
      engine: "xtts",
      model_path,
      speaker_wav: opts.speakerWav.trim() || joinRoot(opts.rootPath, "voices/travis.wav"),
    },
  };
}

export function buildTrainScript(opts: {
  rootPath: string;
  speakerName: string;
  batchSize: number;
  lr: string;
  epochs: number;
}) {
  const output = joinRoot(opts.rootPath, "models/tts/xtts_custom");
  const data = joinRoot(opts.rootPath, `datasets/${slug(opts.speakerName)}_voice`);
  return `from TTS.api import TTS

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
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "") || "speaker";
}
