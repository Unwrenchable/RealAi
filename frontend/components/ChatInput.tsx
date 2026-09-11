"use client";

import {
  useRef,
  useCallback,
  KeyboardEvent,
  ChangeEvent,
} from "react";
import { Send, Square, Cpu } from "lucide-react";
import type { ModelOption } from "@/lib/types";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  isLoading: boolean;
  model: ModelOption | undefined;
  disabled?: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  onStop,
  isLoading,
  model,
  disabled = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
      // Auto-resize
      const el = e.target;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    },
    [onChange]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!isLoading && value.trim()) onSubmit();
      }
    },
    [isLoading, onSubmit, value]
  );

  const canSend = !isLoading && value.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-slate-800 bg-slate-950 px-4 py-3">
      {/* Model badge */}
      <div className="flex items-center gap-1.5 mb-2">
        <Cpu size={11} className="text-slate-500" />
        <span className="text-xs text-slate-500">
          {model?.label ?? "RealAI 2.0"}
        </span>
      </div>

      <div
        className={[
          "flex items-end gap-3 rounded-2xl border px-4 py-3 transition-colors",
          disabled
            ? "border-slate-800 bg-slate-900 opacity-60"
            : "border-slate-700 bg-slate-900 focus-within:border-brand-600",
        ].join(" ")}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Message RealAI… (Shift+Enter for new line)"
          disabled={disabled || isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-slate-100 placeholder-slate-500
                     focus:outline-none leading-relaxed min-h-[24px] max-h-[200px] py-0.5"
        />

        {isLoading ? (
          <button
            onClick={onStop}
            className="flex items-center justify-center w-8 h-8 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors shrink-0"
            title="Stop generating"
          >
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={onSubmit}
            disabled={!canSend}
            className={[
              "flex items-center justify-center w-8 h-8 rounded-xl transition-colors shrink-0",
              canSend
                ? "bg-brand-600 hover:bg-brand-700 text-white"
                : "bg-slate-800 text-slate-600 cursor-not-allowed",
            ].join(" ")}
            title="Send message"
          >
            <Send size={14} />
          </button>
        )}
      </div>

      <p className="text-center text-xs text-slate-600 mt-2">
        RealAI can make mistakes. Verify important information.
      </p>
    </div>
  );
}
