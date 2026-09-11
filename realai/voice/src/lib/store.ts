import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DEFAULT_MODELS_ROOT, type EngineId, joinRoot } from "@/lib/engines";

type DatasetChecks = {
  duration: boolean;
  clean: boolean;
  wav: boolean;
  rate: boolean;
};

type LabState = {
  engineId: EngineId;
  rootPath: string;
  kokoroVoice: string;
  speakerRel: string;
  speakerName: string;
  epochs: number;
  batchSize: number;
  lr: string;
  checks: DatasetChecks;
  lastLine: string;
  setEngine: (id: EngineId) => void;
  setRootPath: (path: string) => void;
  setKokoroVoice: (id: string) => void;
  setSpeakerRel: (rel: string) => void;
  setSpeakerName: (name: string) => void;
  setEpochs: (n: number) => void;
  setBatchSize: (n: number) => void;
  setLr: (lr: string) => void;
  toggleCheck: (key: keyof DatasetChecks) => void;
  setLastLine: (line: string) => void;
  speakerWav: () => string;
};

export const useLab = create<LabState>()(
  persist(
    (set, get) => ({
      engineId: "xtts",
      rootPath: DEFAULT_MODELS_ROOT,
      kokoroVoice: "af_heart",
      speakerRel: "voices/unwrenchable.wav",
      speakerName: "unwrenchable",
      epochs: 300,
      batchSize: 4,
      lr: "1e-4",
      checks: { duration: false, clean: false, wav: false, rate: false },
      lastLine: "",
      setEngine: (engineId) => set({ engineId }),
      setRootPath: (rootPath) => set({ rootPath }),
      setKokoroVoice: (kokoroVoice) => set({ kokoroVoice }),
      setSpeakerRel: (speakerRel) => set({ speakerRel }),
      setSpeakerName: (speakerName) => set({ speakerName }),
      setEpochs: (epochs) => set({ epochs }),
      setBatchSize: (batchSize) => set({ batchSize }),
      setLr: (lr) => set({ lr }),
      toggleCheck: (key) =>
        set((s) => ({ checks: { ...s.checks, [key]: !s.checks[key] } })),
      setLastLine: (lastLine) => set({ lastLine }),
      speakerWav: () => joinRoot(get().rootPath, get().speakerRel),
    }),
    {
      name: "realai-voice-lab",
      skipHydration: true,
      partialize: (s) => ({
        engineId: s.engineId,
        rootPath: s.rootPath,
        kokoroVoice: s.kokoroVoice,
        speakerRel: s.speakerRel,
        speakerName: s.speakerName,
        epochs: s.epochs,
        batchSize: s.batchSize,
        lr: s.lr,
        checks: s.checks,
        lastLine: s.lastLine,
      }),
    },
  ),
);
