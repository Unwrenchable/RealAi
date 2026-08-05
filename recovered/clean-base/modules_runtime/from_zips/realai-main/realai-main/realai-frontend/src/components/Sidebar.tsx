"use client";

import { MessageSquare, Plus, Settings, Trash2, Bot } from "lucide-react";
import type { Conversation } from "@/lib/types";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpenSettings: () => void;
}

function formatDate(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - new Date(date).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(date).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onOpenSettings,
}: SidebarProps) {
  // Group conversations by relative date
  const groups: Record<string, Conversation[]> = {};
  for (const convo of conversations) {
    const label = formatDate(convo.createdAt);
    if (!groups[label]) groups[label] = [];
    groups[label].push(convo);
  }

  return (
    <aside className="flex flex-col w-64 shrink-0 bg-slate-900 border-r border-slate-800 h-full">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-slate-800">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-600">
          <Bot size={16} className="text-white" />
        </div>
        <span className="font-semibold text-base tracking-tight text-slate-100">
          RealAI
        </span>
        <span className="ml-auto text-xs font-medium text-brand-400 bg-brand-900/40 px-1.5 py-0.5 rounded">
          2.0
        </span>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <button
          onClick={onNew}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium rounded-lg
                     bg-brand-600 hover:bg-brand-700 text-white transition-colors duration-150"
        >
          <Plus size={15} />
          New chat
        </button>
      </div>

      {/* Conversation list */}
      <nav className="flex-1 overflow-y-auto px-2 space-y-4 pb-2">
        {Object.keys(groups).length === 0 && (
          <p className="text-xs text-slate-500 text-center mt-6 px-2">
            No conversations yet. Start chatting!
          </p>
        )}
        {Object.entries(groups).map(([label, convos]) => (
          <div key={label}>
            <p className="px-2 py-1 text-xs font-medium text-slate-500 uppercase tracking-wider">
              {label}
            </p>
            <ul className="space-y-0.5">
              {convos.map((convo) => (
                <li key={convo.id}>
                  <button
                    onClick={() => onSelect(convo.id)}
                    className={[
                      "group flex items-center gap-2 w-full px-2 py-2 rounded-lg text-sm text-left transition-colors",
                      activeId === convo.id
                        ? "bg-slate-700 text-slate-100"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-100",
                    ].join(" ")}
                  >
                    <MessageSquare size={13} className="shrink-0 opacity-60" />
                    <span className="flex-1 truncate leading-snug">
                      {convo.title}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(convo.id);
                      }}
                      className="hidden group-hover:flex items-center justify-center w-5 h-5 rounded hover:bg-slate-600 text-slate-400 hover:text-red-400"
                      title="Delete conversation"
                    >
                      <Trash2 size={11} />
                    </button>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800 p-2">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
        >
          <Settings size={14} />
          Settings
        </button>
      </div>
    </aside>
  );
}
