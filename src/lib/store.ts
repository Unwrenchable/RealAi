import { create } from "zustand";
import { persist } from "zustand/middleware";
import { type EngineId, joinRoot } from "@/lib/engines";

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
  grokVoiceId: string;
  customVoiceId: string | null;
  customVoiceName: string | null;
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
  setGrokVoice: (id: string) => void;
  setCustomVoice: (id: string | null, name?: string | null) => void;
  setEpochs: (n: number) => void;
  setBatchSize: (n: number) => void;
  setLr: (lr: string) => void;
  toggleCheck: (key: keyof DatasetChecks) => void;
  setLastLine: (line: string) => void;
  speakerWav: () => string;
};

const DEFAULT_ROOT = "C:/RealAI-clean";

export const useLab = create<LabState>()(
  persist(
    (set, get) => ({
      engineId: "xtts",
      rootPath: DEFAULT_ROOT,
      kokoroVoice: "en_US_male",
      speakerRel: "voices/travis.wav",
      speakerName: "Travis",
      grokVoiceId: "rex",
      customVoiceId: null,
      customVoiceName: null,
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
      setGrokVoice: (grokVoiceId) => set({ grokVoiceId, customVoiceId: null }),
      setCustomVoice: (customVoiceId, customVoiceName = null) =>
        set({ customVoiceId, customVoiceName: customVoiceName ?? null }),
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
        grokVoiceId: s.grokVoiceId,
        customVoiceId: s.customVoiceId,
        customVoiceName: s.customVoiceName,
        epochs: s.epochs,
        batchSize: s.batchSize,
        lr: s.lr,
        checks: s.checks,
        lastLine: s.lastLine,
      }),
    },
  ),
);
