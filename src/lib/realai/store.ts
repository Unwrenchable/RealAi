import { uid } from "@/lib/utils";
import type { ChatMessage, ExecTrace, Thread } from "./types";

const KEY = "realai-hive-v1";

function blankThread(): Thread {
  return {
    id: uid("t"),
    title: "Boot console",
    messages: [],
    createdAt: new Date().toISOString(),
  };
}

export function defaultState() {
  const t = blankThread();
  return { threads: [t] as Thread[], activeId: t.id, log: [] as ExecTrace[] };
}

export type HivePersist = ReturnType<typeof defaultState>;

export function loadState(): HivePersist {
  if (typeof window === "undefined") return defaultState();
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw) as HivePersist;
    if (!parsed.threads?.length) return defaultState();
    return {
      threads: parsed.threads,
      activeId: parsed.activeId || parsed.threads[0].id,
      log: parsed.log ?? [],
    };
  } catch {
    return defaultState();
  }
}

export function saveState(state: HivePersist) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* quota */
  }
}

export function newThread(): Thread {
  return {
    id: uid("t"),
    title: "New thread",
    messages: [],
    createdAt: new Date().toISOString(),
  };
}

export function pushMessage(threads: Thread[], activeId: string, msg: ChatMessage): Thread[] {
  return threads.map((t) => (t.id === activeId ? { ...t, messages: [...t.messages, msg] } : t));
}

export function titleFrom(text: string) {
  const t = text.replace(/\s+/g, " ").trim();
  return t.slice(0, 42) || "New thread";
}
