"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Copy, Check } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface MessageListProps {
  messages: ChatMessage[];
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2 py-1 rounded text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
      title="Copy message"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 items-center h-5 px-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-brand-400"
          style={{
            animation: "typingDot 1.2s infinite ease-in-out",
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

interface BubbleProps {
  message: ChatMessage;
}

function Bubble({ message }: BubbleProps) {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming;

  return (
    <div
      className={[
        "flex gap-3 animate-slide-up",
        isUser ? "flex-row-reverse" : "flex-row",
      ].join(" ")}
    >
      {/* Avatar */}
      <div
        className={[
          "flex items-center justify-center w-8 h-8 rounded-full shrink-0 mt-0.5",
          isUser ? "bg-brand-600" : "bg-slate-700 border border-slate-600",
        ].join(" ")}
      >
        {isUser ? (
          <User size={14} className="text-white" />
        ) : (
          <Bot size={14} className="text-brand-400" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={[
          "flex flex-col gap-1 max-w-[80%]",
          isUser ? "items-end" : "items-start",
        ].join(" ")}
      >
        <span className="text-xs font-medium text-slate-500 px-1">
          {isUser ? "You" : "RealAI"}
        </span>

        <div
          className={[
            "px-4 py-3 rounded-2xl text-sm leading-relaxed",
            isUser
              ? "bg-brand-600 text-white rounded-tr-sm"
              : "bg-slate-800 border border-slate-700 text-slate-100 rounded-tl-sm",
          ].join(" ")}
        >
          {isStreaming ? (
            <TypingIndicator />
          ) : isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-ai">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp + copy */}
        {!isStreaming && (
          <div
            className={[
              "flex items-center gap-2 px-1",
              isUser ? "flex-row-reverse" : "flex-row",
            ].join(" ")}
          >
            <span className="text-xs text-slate-600">
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {!isUser && <CopyButton text={message.content} />}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6 animate-fade-in">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700">
          <Bot size={28} className="text-brand-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-100 mb-1">
            How can I help you today?
          </h2>
          <p className="text-sm text-slate-500 max-w-xs">
            Ask anything — I can chat, write code, analyze images, search the
            web, and much more.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 w-full max-w-sm mt-2">
          {[
            "Explain quantum computing simply",
            "Write a Python web scraper",
            "Summarise the latest AI news",
            "Help plan a business idea",
          ].map((prompt) => (
            <button
              key={prompt}
              className="text-xs text-left px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700
                         text-slate-400 hover:text-slate-100 hover:border-brand-600 hover:bg-slate-800
                         transition-colors duration-150"
              onClick={() => {
                // Dispatch a custom event the page can listen to
                window.dispatchEvent(
                  new CustomEvent("realai:prompt", { detail: prompt })
                );
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-4 py-6">
      {messages.map((msg) => (
        <Bubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
