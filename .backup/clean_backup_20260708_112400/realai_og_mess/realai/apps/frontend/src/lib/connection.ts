export type ConnectionState = "checking" | "connected" | "offline";

export interface HealthResult {
  state: ConnectionState;
  message: string;
  pluginCount?: number;
}

const FETCH_TIMEOUT_MS = 6000;

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const signal =
    init?.signal ??
    (typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(FETCH_TIMEOUT_MS)
      : undefined);
  return fetch(input, { ...init, signal });
}

export async function checkProviderHealth(): Promise<HealthResult> {
  try {
    const res = await fetchWithTimeout("/api/health", { cache: "no-store" });
    const data = await res.json();

    const provider = data.provider as Record<string, unknown> | undefined;
    const liveOk =
      provider?.status === "ok" ||
      provider?.status === "healthy" ||
      data.ok === true;

    if (!res.ok || !liveOk) {
      const base = data.baseUrl || "provider";
      return {
        state: "offline",
        message: data.error
          ? `${base} — ${data.error}`
          : `Cannot reach RealAI provider at ${base}. Start it with: py -3.14 -m realai.provider`,
      };
    }

    const plugins = Array.isArray(provider?.plugins)
      ? (provider.plugins as string[])
      : [];
    const baseUrl = (data.baseUrl as string) || "127.0.0.1:8001";

    return {
      state: "connected",
      message: `Connected — ${baseUrl}${plugins.length ? ` · ${plugins.length} plugins` : ""}`,
      pluginCount: plugins.length,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Network error";
    return {
      state: "offline",
      message: `Health check failed: ${msg}`,
    };
  }
}

export async function fetchProviderModels(): Promise<string[]> {
  try {
    const res = await fetch("/api/models", { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    const rows = Array.isArray(data?.data) ? data.data : [];
    return rows
      .map((row: { id?: string }) => row?.id)
      .filter((id: unknown): id is string => typeof id === "string");
  } catch {
    return [];
  }
}

export async function fetchAgents(): Promise<
  import("@/lib/types").AgentOption[]
> {
  try {
    const res = await fetch("/api/agents", { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    const rows = Array.isArray(data?.data) ? data.data : [];
    return rows.map((row: Record<string, unknown>) => ({
      id: String(row.id ?? ""),
      name: String(row.name ?? row.id ?? "Agent"),
      description:
        typeof row.description === "string" ? row.description : undefined,
      type: typeof row.type === "string" ? row.type : undefined,
      capabilities: Array.isArray(row.capabilities)
        ? (row.capabilities as string[])
        : undefined,
      preferredProfile:
        typeof row.preferred_profile === "string"
          ? row.preferred_profile
          : undefined,
      riskLevel:
        typeof row.risk_level === "string" ? row.risk_level : undefined,
    }));
  } catch {
    return [];
  }
}

export async function fetchCapabilities(): Promise<string[]> {
  try {
    const res = await fetch("/api/capabilities", { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    const rows = Array.isArray(data?.data) ? data.data : [];
    return rows
      .map((row: { id?: string }) => row?.id)
      .filter((id: unknown): id is string => typeof id === "string");
  } catch {
    return [];
  }
}