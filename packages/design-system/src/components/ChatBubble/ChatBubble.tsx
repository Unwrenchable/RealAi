import React from "react";
import { Avatar } from "../Avatar/Avatar";

export interface ChatBubbleProps {
  message: string;
  role: "user" | "assistant" | "system";
  timestamp?: string;
  avatarSrc?: string;
  avatarName?: string;
  className?: string;
  isLoading?: boolean;
}

export function ChatBubble({
  message,
  role,
  timestamp,
  avatarSrc,
  avatarName,
  className = "",
  isLoading = false,
}: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={["flex gap-3", isUser ? "flex-row-reverse" : "flex-row", className].join(" ")}>
      <Avatar
        src={avatarSrc}
        name={avatarName ?? (isUser ? "User" : "RealAI")}
        size="sm"
      />
      <div className={["max-w-[75%]", isUser ? "items-end" : "items-start", "flex flex-col gap-1"].join(" ")}>
        <div
          className={[
            "px-4 py-2.5 rounded-2xl text-sm leading-relaxed",
            isUser
              ? "bg-indigo-600 text-white rounded-tr-sm"
              : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm",
          ].join(" ")}
        >
          {isLoading ? (
            <div className="flex gap-1 items-center h-5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full bg-current opacity-60 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          ) : (
            message
          )}
        </div>
        {timestamp && <span className="text-xs text-gray-400 px-1">{timestamp}</span>}
      </div>
    </div>
  );
}
