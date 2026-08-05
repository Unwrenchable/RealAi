"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Menu, X, AlertCircle } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import ChatInput from "@/components/ChatInput";
import SettingsDrawer from "@/components/SettingsDrawer";
import type { Conversation, ChatMessage, Settings } from "@/lib/types";
import { DEFAULT_SETTINGS, DEFAULT_MODELS } from "@/lib/types";
import { sendMessage } from "@/lib/realai";

function uuid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function deriveTitle(content: string): string {
  const clean = content.replace(/\s+/g, " ").trim();
  return clean.length > 48 ? clean.slice(0, 48) + "…" : clean;
}

function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem("realai:settings");
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    // ignore
  }
  return DEFAULT_SETTINGS;
}

function saveSettings(s: Settings) {
  try {
    localStorage.setItem("realai:settings", JSON.stringify(s));
  } catch {
    // ignore
  }
}

function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem("realai:conversations");
    if (raw) {
      const parsed = JSON.parse(raw) as Conversation[];
      // Revive Date objects
      return parsed.map((c) => ({
        ...c,
        createdAt: new Date(c.createdAt),
        messages: c.messages.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        })),
      }));
    }
  } catch {
    // ignore
  }
  return [];
}

function saveConversations(convos: Conversation[]) {
  try {
    localStorage.setItem("realai:conversations", JSON.stringify(convos));
  } catch {
    // ignore
  }
}

export default function HomePage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  // Hydrate from localStorage
  useEffect(() => {
    setSettings(loadSettings());
    const convos = loadConversations();
    setConversations(convos);
    if (convos.length > 0) setActiveId(convos[0].id);
  }, []);

  // Persist conversations
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Persist settings
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  // Listen for prompt suggestions from MessageList's empty state
  useEffect(() => {
    function handlePrompt(e: Event) {
      const prompt = (e as CustomEvent<string>).detail;
      setInput(prompt);
    }
    window.addEventListener("realai:prompt", handlePrompt);
    return () => window.removeEventListener("realai:prompt", handlePrompt);
  }, []);

  const activeConvo = conversations.find((c) => c.id === activeId) ?? null;
  const activeModel = DEFAULT_MODELS.find((m) => m.id === settings.model);

  const createConversation = useCallback((): Conversation => {
    const convo: Conversation = {
      id: uuid(),
      title: "New conversation",
      messages: [],
      createdAt: new Date(),
      model: settings.model,
    };
    setConversations((prev) => [convo, ...prev]);
    setActiveId(convo.id);
    return convo;
  }, [settings.model]);

  const handleNew = useCallback(() => {
    createConversation();
    setInput("");
    setError(null);
  }, [createConversation]);

  const handleSelect = useCallback((id: string) => {
    setActiveId(id);
    setError(null);
  }, []);

  const handleDelete = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setActiveId((prev) => {
      if (prev !== id) return prev;
      const remaining = conversations.filter((c) => c.id !== id);
      return remaining.length > 0 ? remaining[0].id : null;
    });
  }, [conversations]);

  const handleSubmit = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setError(null);
    setInput("");

    // Ensure there's an active conversation
    let convoId = activeId;
    let convo = conversations.find((c) => c.id === convoId);
    if (!convo) {
      convo = createConversation();
      convoId = convo.id;
    }

    const userMsg: ChatMessage = {
      id: uuid(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    const placeholderMsg: ChatMessage = {
      id: uuid(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
    };

    // Optimistically add user message + placeholder
    setConversations((prev) =>
      prev.map((c) =>
        c.id === convoId
          ? {
              ...c,
              title:
                c.messages.length === 0 ? deriveTitle(text) : c.title,
              messages: [...c.messages, userMsg, placeholderMsg],
            }
          : c
      )
    );

    setIsLoading(true);
    abortRef.current = new AbortController();

    try {
      const allMessages = [...(convo.messages), userMsg];
      const response = await sendMessage(allMessages, settings);

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convoId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === placeholderMsg.id
                    ? { ...m, content: response, isStreaming: false }
                    : m
                ),
              }
            : c
        )
      );
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Something went wrong. Try again.";
      setError(msg);

      // Remove placeholder on error
      setConversations((prev) =>
        prev.map((c) =>
          c.id === convoId
            ? {
                ...c,
                messages: c.messages.filter((m) => m.id !== placeholderMsg.id),
              }
            : c
        )
      );
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  }, [input, isLoading, activeId, conversations, createConversation, settings]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
    // Remove any streaming placeholder
    setConversations((prev) =>
      prev.map((c) => ({
        ...c,
        messages: c.messages.filter((m) => !m.isStreaming),
      }))
    );
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={[
          "fixed md:relative z-40 md:z-auto h-full transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          sidebarOpen ? "md:flex" : "hidden md:flex",
        ].join(" ")}
      >
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => {
            handleSelect(id);
            setSidebarOpen(false);
          }}
          onNew={() => {
            handleNew();
            setSidebarOpen(false);
          }}
          onDelete={handleDelete}
          onOpenSettings={() => {
            setSettingsOpen(true);
            setSidebarOpen(false);
          }}
        />
      </div>

      {/* Main */}
      <main className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        {/* Header */}
        <header className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 bg-slate-950 shrink-0">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors md:hidden"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="hidden md:flex p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <Menu size={18} />
          </button>

          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-slate-100 truncate">
              {activeConvo?.title ?? "RealAI"}
            </h1>
          </div>

          {/* Model pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-xs text-slate-300 font-medium">
              {activeModel?.label ?? "RealAI 2.0"}
            </span>
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mt-3 flex items-center gap-2 px-4 py-3 rounded-xl bg-red-950/60 border border-red-800 text-sm text-red-300">
            <AlertCircle size={15} className="shrink-0" />
            <span className="flex-1">{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-200"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto w-full h-full">
            <MessageList messages={activeConvo?.messages ?? []} />
          </div>
        </div>

        {/* Input */}
        <div className="max-w-3xl mx-auto w-full">
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            onStop={handleStop}
            isLoading={isLoading}
            model={activeModel}
            disabled={false}
          />
        </div>
      </main>

      {/* Settings drawer */}
      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={setSettings}
      />
    </div>
  );
}
