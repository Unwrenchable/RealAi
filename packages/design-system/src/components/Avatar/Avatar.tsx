import React, { useState } from "react";

export interface AvatarProps {
  src?: string;
  alt?: string;
  name?: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
  status?: "online" | "offline" | "away" | "busy";
}

const sizeClasses = {
  xs: "w-6 h-6 text-xs",
  sm: "w-8 h-8 text-sm",
  md: "w-10 h-10 text-base",
  lg: "w-12 h-12 text-lg",
  xl: "w-16 h-16 text-xl",
};

const statusClasses = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  away: "bg-yellow-500",
  busy: "bg-red-500",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter((n) => n.length > 0)
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Avatar({ src, alt, name, size = "md", className = "", status }: AvatarProps) {
  const [imgError, setImgError] = useState(false);

  return (
    <div className={["relative inline-flex", className].join(" ")}>
      <div
        className={[
          "rounded-full overflow-hidden flex items-center justify-center",
          "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-medium",
          sizeClasses[size],
        ].join(" ")}
      >
        {src && !imgError ? (
          <img src={src} alt={alt ?? name} className="w-full h-full object-cover" onError={() => setImgError(true)} />
        ) : name ? (
          <span>{getInitials(name)}</span>
        ) : (
          <svg className="w-1/2 h-1/2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        )}
      </div>
      {status && (
        <span
          className={[
            "absolute bottom-0 right-0 rounded-full ring-2 ring-white dark:ring-gray-800",
            statusClasses[status],
            size === "xs" || size === "sm" ? "w-2 h-2" : "w-3 h-3",
          ].join(" ")}
        />
      )}
    </div>
  );
}
