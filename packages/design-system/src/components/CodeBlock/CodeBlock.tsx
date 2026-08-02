import React, { useState } from "react";
import { CopyIcon } from "../../icons/CopyIcon";

export interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  filename?: string;
  className?: string;
}

export function CodeBlock({ code, language = "text", showLineNumbers = false, filename, className = "" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable (non-secure context or permission denied)
    }
  };

  const lines = code.split("\n");

  return (
    <div className={["rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700", className].join(" ")}>
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          {filename && <span className="text-sm text-gray-500 dark:text-gray-400">{filename}</span>}
          <span className="text-xs font-mono text-gray-400 uppercase">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
        >
          <CopyIcon size={14} />
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 bg-gray-950 dark:bg-gray-900 text-sm font-mono">
        {showLineNumbers ? (
          lines.map((line, i) => (
            <div key={i} className="flex">
              <span className="select-none w-8 text-gray-600 text-right mr-4 shrink-0">{i + 1}</span>
              <code className="text-gray-100">{line}</code>
            </div>
          ))
        ) : (
          <code className="text-gray-100">{code}</code>
        )}
      </pre>
    </div>
  );
}
