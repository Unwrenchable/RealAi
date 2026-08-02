import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
}

export function Input({
  label,
  helperText,
  error,
  leftAddon,
  rightAddon,
  className = "",
  id,
  ...props
}: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftAddon && (
          <div className="absolute left-3 text-gray-400">{leftAddon}</div>
        )}
        <input
          id={inputId}
          {...props}
          className={[
            "w-full rounded-lg border bg-white dark:bg-gray-800 px-3 py-2 text-sm",
            "text-gray-900 dark:text-gray-100 placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "transition-colors",
            error
              ? "border-red-500 focus:ring-red-500"
              : "border-gray-300 dark:border-gray-600",
            leftAddon ? "pl-10" : "",
            rightAddon ? "pr-10" : "",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            className,
          ].join(" ")}
        />
        {rightAddon && (
          <div className="absolute right-3 text-gray-400">{rightAddon}</div>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {helperText && !error && <p className="text-xs text-gray-500">{helperText}</p>}
    </div>
  );
}
