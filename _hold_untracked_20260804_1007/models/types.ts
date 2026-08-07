export interface ModelManifest {
  name: string;
  version: string;
  provider: string;
  context: number;
  type: "text" | "vision" | "audio" | "embedding";
  description: string;
  capabilities: string[];
  tags?: string[];
}