export type GrokVoice = {
  id: string;
  name: string;
  tone: string;
};

/** Curated Grok Voice ids for in-browser preview. Local engines stay in the pipeline JSON. */
export const GROK_VOICES: GrokVoice[] = [
  { id: "rex", name: "Rex", tone: "Confident, clear" },
  { id: "leo", name: "Leo", tone: "Authoritative" },
  { id: "orion", name: "Orion", tone: "Cinematic" },
  { id: "atlas", name: "Atlas", tone: "Commanding" },
  { id: "lux", name: "Lux", tone: "Grounded, calm" },
  { id: "perseus", name: "Perseus", tone: "Strong" },
  { id: "helix", name: "Helix", tone: "Bold, dynamic" },
  { id: "eve", name: "Eve", tone: "Energetic" },
];

export const SAMPLE_LINES = [
  "RealAI is online. Inference backend switched. Voice check, one two three.",
  "This is a local stack. Kokoro, Fish Speech, and XTTS share one config key.",
  "Two to five minutes of clean audio is enough to clone a voice on XTTS.",
];

export const MAX_TTS_CHARS = 420;
