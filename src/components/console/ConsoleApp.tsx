import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Menu, X } from "lucide-react";
import { Rail } from "./Rail";
import { Feed } from "./Feed";
import { Composer, type ComposerMode } from "./Composer";
import { Ops } from "./Ops";
import { ScriptPad } from "./ScriptPad";
import { ToolCard } from "./ToolCard";
import { askRealai, execCommand, listHiveFiles, probeHive, readHivePath } from "@/lib/realai/actions";
import {
  defaultState,
  loadState,
  newThread,
  pushMessage,
  saveState,
  titleFrom,
  type HivePersist,
} from "@/lib/realai/store";
import { cn, uid } from "@/lib/utils";
import type { ChatMessage, ExecTrace, HiveFile, HiveStatus } from "@/lib/realai/types";

type StageTab = "chat" | "scripts" | "files";

const ORCH =
  (typeof import.meta !== "undefined" &&
    (import.meta as { env?: Record<string, string> }).env?.VITE_REALAI_API_BASE) ||
  "http://127.0.0.1:8001";

async function speakViaOrch(text: string) {
  const spoken = String(text || "").slice(0, 1200);
  if (!spoken) return;
  try {
    const res = await fetch(`${ORCH}/v1/audio/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-RealAI-Voice": "on" },
      body: JSON.stringify({ input: spoken, model: "tts-1" }),
      signal: AbortSignal.timeout(45000),
    });
    const data = (await res.json()) as { audio_b64?: string; bytes?: number; format?: string };
    if (data.audio_b64 && Number(data.bytes || 0) > 64) {
      const mime = data.format === "mp3" ? "audio/mpeg" : "audio/wav";
      const audio = new Audio(`data:${mime};base64,${data.audio_b64}`);
      await audio.play().catch(() => undefined);
      return;
    }
  } catch {
    /* fall through to browser TTS */
  }
  try {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(spoken));
  } catch {
    /* ignore */
  }
}

export function ConsoleApp() {
  const [state, setState] = useState<HivePersist>(defaultState);
  const [hydrated, setHydrated] = useState(false);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<ComposerMode>("ask");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState<HiveStatus | null>(null);
  const [files, setFiles] = useState<HiveFile[]>([]);
  const [tab, setTab] = useState<StageTab>("chat");
  const [filePreview, setFilePreview] = useState<{ path: string; body: string } | null>(null);
  const [railOpen, setRailOpen] = useState(false);
  const [clock, setClock] = useState("");
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setState(loadState());
    setHydrated(true);
    const tick = () => setClock(new Date().toLocaleTimeString());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (hydrated) saveState(state);
  }, [state, hydrated]);

  const refreshHive = useCallback(async () => {
    try {
      const [st, listing] = await Promise.all([probeHive(), listHiveFiles({ data: { path: "." } })]);
      setStatus(st);
      if (listing.ok) {
        const nested = await Promise.all(
          listing.files
            .filter((f) => f.type === "dir")
            .map((d) => listHiveFiles({ data: { path: d.path } })),
        );
        const kids = nested.flatMap((n) => (n.ok ? n.files : []));
        setFiles([...listing.files, ...kids]);
      }
    } catch {
      setStatus((s) => s ?? { ok: false, cwd: "", python: "?", node: "?", bash: "?", files: 0 });
    }
  }, []);

  useEffect(() => {
    void refreshHive();
  }, [refreshHive]);

  const active = useMemo(
    () => state.threads.find((t) => t.id === state.activeId) ?? state.threads[0],
    [state.threads, state.activeId],
  );

  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [active?.messages.length, pending, tab]);

  const pushLog = (trace: ExecTrace) => {
    setState((s) => ({ ...s, log: [trace, ...s.log].slice(0, 40) }));
    void refreshHive();
  };

  const append = (msg: ChatMessage, title?: string) => {
    setState((s) => {
      const threads = pushMessage(s.threads, s.activeId, msg).map((t) =>
        t.id === s.activeId && title && t.messages.length <= 1 ? { ...t, title } : t,
      );
      return { ...s, threads };
    });
  };

  const submit = async () => {
    const text = draft.trim();
    if (!text || pending) return;
    setDraft("");
    setTab("chat");
    setRailOpen(false);

    const userMsg: ChatMessage = {
      id: uid("m"),
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    const title = active.messages.length === 0 ? titleFrom(text) : undefined;
    append(userMsg, title);
    setPending(true);

    try {
      if (mode === "run") {
        const res = await execCommand({ data: { command: text.replace(/^\$\s*/, "") } });
        pushLog(res.trace);
        append({
          id: uid("m"),
          role: "assistant",
          content: res.trace.exitCode === 0 ? "" : "Command finished with a non-zero exit. Output is live above.",
          traces: [res.trace],
          createdAt: new Date().toISOString(),
        });
      } else {
        const history = [...active.messages, userMsg].map((m) => ({
          role: m.role,
          content: m.content,
        }));
        const res = await askRealai({
          data: {
            history: history.slice(0, -1),
            userText: text,
          },
        });
        for (const t of res.traces) pushLog(t);
        append({
          id: uid("m"),
          role: "assistant",
          content: res.reply,
          traces: res.traces,
          missedExec: res.missedExec,
          createdAt: new Date().toISOString(),
        });
        // Speak aloud via local orch TTS (Windows SAPI / Kokoro) — never cloud.
        const spoken = res.spokenText || res.reply;
        if (spoken && typeof window !== "undefined") {
          void speakViaOrch(spoken);
        }
      }
    } catch (err) {
      append({
        id: uid("m"),
        role: "assistant",
        content: `Hive failed closed: ${err instanceof Error ? err.message : String(err)}`,
        createdAt: new Date().toISOString(),
      });
    } finally {
      setPending(false);
    }
  };

  const onChip = (prompt: string, chipMode: ComposerMode) => {
    setMode(chipMode);
    setDraft(prompt);
  };

  const onNew = () => {
    const t = newThread();
    setState((s) => ({ ...s, threads: [t, ...s.threads], activeId: t.id }));
    setTab("chat");
    setRailOpen(false);
  };

  const onOpenFile = async (path: string) => {
    const file = files.find((f) => f.path === path);
    if (file?.type === "dir") return;
    try {
      const trace = await readHivePath({ data: { path } });
      setFilePreview({ path, body: trace.stdout || trace.stderr });
      setTab("files");
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-ink lg:grid lg:grid-cols-[268px_1fr] xl:grid-cols-[268px_1fr_300px]">
      {railOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-ink/70"
            aria-label="Close menu"
            onClick={() => setRailOpen(false)}
          />
          <div className="relative z-10 flex h-full w-[min(84vw,280px)] flex-col bg-rail shadow-[var(--shadow-border)]">
            <div className="flex justify-end p-2">
              <button
                type="button"
                className="grid size-11 place-items-center text-mute"
                onClick={() => setRailOpen(false)}
                aria-label="Close"
              >
                <X className="size-5" />
              </button>
            </div>
            <Rail
              className="flex h-full min-h-0"
              threads={state.threads}
              activeId={state.activeId}
              status={status}
              onNew={onNew}
              onSelect={(id) => {
                setState((s) => ({ ...s, activeId: id }));
                setRailOpen(false);
              }}
            />
          </div>
        </div>
      ) : null}

      <Rail
        className="hidden border-r border-line lg:flex"
        threads={state.threads}
        activeId={state.activeId}
        status={status}
        onNew={onNew}
        onSelect={(id) => setState((s) => ({ ...s, activeId: id }))}
      />

      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line px-3 backdrop-blur-md sm:px-4">
          <button
            type="button"
            className="grid size-11 place-items-center text-mute lg:hidden"
            onClick={() => setRailOpen(true)}
            aria-label="Open threads"
          >
            <Menu className="size-5" />
          </button>
          <div className="hidden items-center gap-2 rounded-full bg-elevated px-3 py-1.5 font-mono text-xs shadow-[var(--shadow-border)] sm:flex">
            <span
              className={cn(
                "inline-block size-1.5 rounded-full",
                status?.ok ? "live-dot bg-acid" : "bg-hot",
              )}
            />
            realai-hive
          </div>
          <div className="hidden rounded-full bg-elevated px-3 py-1.5 font-mono text-xs text-mute shadow-[var(--shadow-border)] md:block">
            exec · live · fail closed
          </div>
          <div className="ml-auto flex items-center gap-1 rounded-full bg-ink p-0.5 shadow-[var(--shadow-border)]">
            {(["chat", "scripts", "files"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={cn(
                  "min-h-9 rounded-full px-3 font-mono text-xs uppercase tracking-widest transition-colors duration-150",
                  tab === t ? "bg-elevated text-acid" : "text-mute hover:text-text",
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="hidden rounded-full bg-elevated px-3 py-1.5 font-mono text-xs tabular-nums text-acid shadow-[var(--shadow-border)] sm:block">
            {clock}
          </div>
        </header>

        <div ref={feedRef} className="min-h-0 flex-1 overflow-auto px-4 py-6 sm:px-8">
          {tab === "chat" ? (
            <Feed messages={active?.messages ?? []} pending={pending} onChip={onChip} />
          ) : null}
          {tab === "scripts" ? <ScriptPad onTrace={pushLog} /> : null}
          {tab === "files" ? (
            <div className="mx-auto w-full max-w-3xl">
              <h2 className="text-xl font-semibold tracking-tight">Hive files</h2>
              <p className="mt-1 mb-4 text-sm text-mute">
                Sandbox at {status?.cwd || "realai-hive"}. Click a file to read it live.
              </p>
              <ul className="mb-4 divide-y divide-line rounded-lg bg-panel shadow-[var(--shadow-border)]">
                {files.map((f) => (
                  <li key={f.path}>
                    <button
                      type="button"
                      className="flex min-h-12 w-full items-center justify-between px-4 text-left text-sm"
                      onClick={() => void onOpenFile(f.path)}
                    >
                      <span className="font-mono text-xs">{f.path}{f.type === "dir" ? "/" : ""}</span>
                      <span className="font-mono text-xs tabular-nums text-mute">{f.type === "file" ? f.size : "dir"}</span>
                    </button>
                  </li>
                ))}
              </ul>
              {filePreview ? (
                <pre className="max-h-[50vh] overflow-auto rounded-lg bg-ink p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap shadow-[var(--shadow-border)]">
                  <span className="mb-2 block text-ice">{filePreview.path}</span>
                  {filePreview.body}
                </pre>
              ) : null}
              {state.log[0] ? (
                <div className="mt-4">
                  <ToolCard trace={state.log[0]} />
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {tab === "chat" ? (
          <div className="shrink-0 px-4 pb-5 pt-2 sm:px-8">
            <Composer
              value={draft}
              mode={mode}
              disabled={pending}
              onChange={setDraft}
              onMode={setMode}
              onSubmit={() => void submit()}
            />
          </div>
        ) : null}
      </section>

      <Ops status={status} log={state.log} files={files} onOpenFile={(p) => void onOpenFile(p)} />
    </div>
  );
}
