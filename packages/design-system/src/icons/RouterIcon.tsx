import React from "react";

interface IconProps { className?: string; size?: number; }

export function RouterIcon({ className, size = 24 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M6.3 6.3a8 8 0 0 0 0 11.4" />
      <path d="M17.7 6.3a8 8 0 0 1 0 11.4" />
      <path d="M3.6 3.6a13 13 0 0 0 0 16.8" />
      <path d="M20.4 3.6a13 13 0 0 1 0 16.8" />
    </svg>
  );
}
