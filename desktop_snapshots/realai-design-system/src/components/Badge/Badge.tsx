import React from "react";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "primary" | "success" | "warning" | "error" | "info";
  size?: "sm" | "md";
  dot?: boolean;
  className?: string;
}

const variantClasses = {
  default: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  primary: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
  success: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  warning: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  info: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
};

const dotColors = {
  default: "bg-gray-500",
  primary: "bg-indigo-500",
  success: "bg-green-500",
  warning: "bg-yellow-500",
  error: "bg-red-500",
  info: "bg-blue-500",
};

export function Badge({ children, variant = "default", size = "sm", dot = false, className = "" }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 font-medium rounded-full",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
        variantClasses[variant],
        className,
      ].join(" ")}
    >
      {dot && <span className={["w-1.5 h-1.5 rounded-full", dotColors[variant]].join(" ")} />}
      {children}
    </span>
  );
}
