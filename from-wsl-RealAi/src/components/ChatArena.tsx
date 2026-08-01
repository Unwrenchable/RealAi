"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";
import { Play, Copy } from "lucide-react";

export default function ChatArena({ persona, godMode }: any) {
  const [messages, setMessages] = useState<any[]>([
    { id: 1, role: "assistant", content: "Hello. I am RealAI — limitless, local-first, and ready to build reality with you." }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { id: Date.now(), role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    // TODO: Connect to your real backend here
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: "assistant",
        content: "Understood. Working on it with full agent orchestration...",
        toolCalls: [
          { tool: "Web Search", status: "completed", result: "Found 12 competitors..." },
          { tool: "Code Generator", status: "completed", result: "Generated full Next.js app" }
        ]
      }]);
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-8" id="chat-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-3xl ${msg.role === "user" ? "bg-violet-600" : "bg-zinc-900"} rounded-3xl px-6 py-4`}>
              <ReactMarkdown className="prose prose-invert max-w-none">{msg.content}</ReactMarkdown>

              {msg.toolCalls && (
                <div className="mt-6 space-y-4">
                  {msg.toolCalls.map((call: any, i: number) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-black/50 border border-zinc-700 rounded-2xl p-5"
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">⚙️</span>
                          <div>
                            <p className="font-semibold">{call.tool}</p>
                            <p className="text-emerald-400 text-xs">✓ Completed</p>
                          </div>
                        </div>
                        <button className="text-zinc-400 hover:text-white"><Copy size={18} /></button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-3 text-zinc-400">
            <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
            Thinking across agents...
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 border-t border-zinc-800 bg-zinc-950">
        <div className="max-w-4xl mx-auto relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
            placeholder="Ask me anything... I can build businesses, run research, generate code, and more."
            className="w-full bg-zinc-900 border border-zinc-700 rounded-3xl px-7 py-5 text-lg resize-y min-h-[60px] max-h-[200px] focus:outline-none focus:border-violet-500"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim()}
            className="absolute bottom-4 right-4 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 px-8 py-2.5 rounded-2xl font-medium"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}