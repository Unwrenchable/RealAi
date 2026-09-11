import { KOKORO_VOICES } from "@/lib/engines";

export type LabVoice = {
  id: string;
  name: string;
  tone: string;
};

/** Curated local Kokoro voices for in-lab preview (no cloud). */
export const LAB_VOICES: LabVoice[] = KOKORO_VOICES.map((v) => ({
  id: v.id,
  name: v.label,
  tone: "Local Kokoro pack",
}));

export const SAMPLE_LINES = [
  "RealAI is online. Inference is local. Voice check, one two three.",
  "This stack is Kokoro, Fish Speech, and XTTS under checkpoints_lora.",
  "Hive bot can speak on this PC. Vulkan chat is on the AMD server.",
];

export const MAX_TTS_CHARS = 420;
