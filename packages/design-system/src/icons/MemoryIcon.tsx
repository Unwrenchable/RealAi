import React from "react";

interface IconProps { className?: string; size?: number; }

export function MemoryIcon({ className, size = 24 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <path d="M6 12h.01M10 12h.01M14 12h.01M18 12h.01" />
      <path d="M6 9v6M10 9v6M14 9v6M18 9v6" />
    </svg>
  );
}
