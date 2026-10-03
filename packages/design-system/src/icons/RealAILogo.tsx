import React from "react";

interface IconProps {
  className?: string;
  size?: number;
}

export function RealAILogo({ className, size = 32 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect width="32" height="32" rx="8" fill="#6366f1" />
      <path
        d="M8 22L13 10L16 17L19 13L24 22"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="22" cy="10" r="2" fill="white" />
    </svg>
  );
}
