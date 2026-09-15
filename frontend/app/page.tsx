"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { sendMessage } from "@/lib/realai";
import {
  ChatMessage,
  DEFAULT_MODELS,
  DEFAULT_SETTINGS,
  Settings,
} from "@/lib/types";

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function HomePage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [models, setModels] = useState(DEFAULT_MODELS);
  const [apiBase, setApiBase] = useState("…");
  const bottomRef = useRef<HTMLDivElement>(null);

  const localConsole = process.env.NEXT_PUBLIC_LOCAL_CONSOLE_URL || "";

  useEffect(() => {
    setApiBase(process.env.NEXT_PUBLIC_API_URL || "(not set)");
    fetch("/api/models")
      .then((r) => r.json())
      .then((data) => {
        const rows = Array.isArray(data?.data)
          ? data.data.map((m: any) => ({
              id: String(m.id),
              label: String(m.id),
              description: m.owned_by ? `owner ${m.owned_by}` : "from API",
            }))
          : null;
        if (rows?.length) setModels(rows);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !busy,
    [input, busy]
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    const text = input.trim();
    setInput("");
    setError(null);

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    const next = [...messages, userMsg];
    setMessages(next);
    setBusy(true);
    try {
      const reply = await sendMessage(next, settings);
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: reply,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-[#07070b] text-slate-100">
      <header className="flex flex-wrap items-center gap-3 border-b border-white/10 px-4 py-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-sm font-semibold tracking-wide text-[#d6ff3f]">
            RealAI Cloud UI
          </h1>
          <p className="truncate text-xs text-slate-400">
            API: {apiBase} · chat via <code className="text-slate-300">/api/chat</code>
          </p>
        </div>
        <label htmlFor="cloud-model" className="flex items-center gap-2 text-xs text-slate-300">
          Model
          <select
            id="cloud-model"
            name="model"
            className="rounded border border-white/15 bg-black/40 px-2 py-1"
            value={settings.model}
            onChange={(e) =>
              setSettings((s) => ({ ...s, model: e.target.value }))
            }
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        {localConsole ? (
          <a
            className="rounded border border-white/15 px-2 py-1 text-xs text-slate-300 hover:border-[#d6ff3f]/hover:text-[#d6ff3f]"
            href={localConsole}
            target="_blank"
            rel="noreferrer"
          >
            Local Hive console
          </a>
        ) : null}
      </header>

      <main className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="mx-auto mt-16 max-w-lg rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-slate-300">
            <p className="mb-2 font-medium text-slate-100">Cloud chat</p>
            <p>
              This Vercel app talks to your public API (
              <code className="text-[#7af0ff]">NEXT_PUBLIC_API_URL</code>
              ). It does <strong>not</strong> redirect to{" "}
              <code>127.0.0.1:8001</code>.
            </p>
            <p className="mt-2 text-slate-400">
              Full GPU Hive console stays on your PC at{" "}
              <code>http://127.0.0.1:8001/console</code>.
            </p>
          </div>
        ) : null}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`mx-auto max-w-3xl rounded-xl px-4 py-3 text-sm leading-relaxed ${
              m.role === "user"
                ? "bg-[#1a1a3e] text-slate-100"
                : "border border-white/10 bg-black/30 text-slate-200"
            }`}
          >
            <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">
              {m.role}
            </div>
            <pre className="whitespace-pre-wrap font-sans">{m.content}</pre>
          </div>
        ))}
        {busy ? (
          <div className="mx-auto max-w-3xl text-xs text-slate-500">Thinking…</div>
        ) : null}
        {error ? (
          <div className="mx-auto max-w-3xl rounded-lg border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        ) : null}
        <div ref={bottomRef} />
      </main>

      <form
        onSubmit={onSubmit}
        className="border-t border-white/10 bg-black/40 px-4 py-3"
      >
        <div className="mx-auto flex max-w-3xl gap-2">
          <textarea
            id="cloud-message"
            name="message"
            className="min-h-[48px] flex-1 resize-none rounded-xl border border-white/15 bg-[#0c0c12] px-3 py-2 text-sm outline-none focus:border-[#d6ff3f]/50"
            placeholder="Message RealAI…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void onSubmit(e as unknown as FormEvent);
              }
            }}
          />
          <button
            type="submit"
            disabled={!canSend}
            className="rounded-xl bg-[#d6ff3f] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
