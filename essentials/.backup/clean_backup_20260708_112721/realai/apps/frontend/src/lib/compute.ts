export type ComputeMode = "auto" | "gpu" | "cpu" | "hybrid";

export interface ComputeStatus {
  mode: ComputeMode;
  recommended_mode: ComputeMode;
  gpu_present: boolean;
  display_gpu_present?: boolean;
  has_amd?: boolean;
  has_nvidia?: boolean;
  accelerator_notes?: string[];
  display_gpus?: Array<{
    name: string;
    vendor?: string;
    vram_gb?: number;
    notes?: string;
  }>;
  resolved_devices?: {
    llm?: string;
    image?: string;
    embedding?: string;
  };
  llama_gpu_layers?: number;
  inference_backend_hint?: string;
  hardware?: {
    platform?: string;
    cpu_count?: number;
    ram_gb?: number;
    torch?: {
      available?: boolean;
      version?: string;
      cuda?: {
        available?: boolean;
        devices?: Array<{
          index: number;
          name: string;
          vram_gb?: number;
          vram_free_gb?: number;
        }>;
      };
      mps?: { available?: boolean };
    };
    backends?: Record<string, boolean>;
  };
}

export const COMPUTE_MODE_LABELS: Record<
  ComputeMode,
  { title: string; description: string }
> = {
  auto: {
    title: "Auto",
    description: "Detects your GPU/CPU and picks the best mix",
  },
  gpu: {
    title: "GPU",
    description: "Max speed — CUDA/MPS when available",
  },
  cpu: {
    title: "CPU only",
    description: "Stable, no VRAM — best for low-RAM machines",
  },
  hybrid: {
    title: "Hybrid",
    description: "GPU for images/embeddings, shared GPU+CPU for chat",
  },
};

export async function fetchComputeStatus(): Promise<ComputeStatus | null> {
  try {
    const res = await fetch("/api/compute", { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as ComputeStatus;
  } catch {
    return null;
  }
}

export async function setComputeMode(mode: ComputeMode): Promise<ComputeStatus | null> {
  try {
    const res = await fetch("/api/compute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) return null;
    return (await res.json()) as ComputeStatus;
  } catch {
    return null;
  }
}