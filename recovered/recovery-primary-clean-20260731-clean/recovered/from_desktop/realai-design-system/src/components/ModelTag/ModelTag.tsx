import React from "react";

export interface ModelTagProps {
  provider: string;
  model: string;
  className?: string;
  size?: "sm" | "md";
}

const providerColors: Record<string, string> = {
  openai: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300",
  anthropic: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  gemini: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  grok: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  mistral: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  together: "bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300",
  deepseek: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300",
  openrouter: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  perplexity: "bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300",
};

export function ModelTag({ provider, model, className = "", size = "sm" }: ModelTagProps) {
  const colorClass = providerColors[provider.toLowerCase()] ?? "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 font-mono rounded-full font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
        colorClass,
        className,
      ].join(" ")}
    >
      <span className="font-sans font-semibold">{provider}</span>
      <span className="opacity-50">/</span>
      <span>{model}</span>
    </span>
  );
}
