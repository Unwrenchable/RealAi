import React from "react";

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helperText?: string;
  error?: string;
  resize?: "none" | "both" | "horizontal" | "vertical";
}

export function TextArea({
  label,
  helperText,
  error,
  resize = "vertical",
  className = "",
  id,
  ...props
}: TextAreaProps) {
  const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={textareaId} className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <textarea
        id={textareaId}
        {...props}
        style={{ resize }}
        className={[
          "w-full rounded-lg border bg-white dark:bg-gray-800 px-3 py-2 text-sm",
          "text-gray-900 dark:text-gray-100 placeholder-gray-400",
          "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
          "min-h-[80px] transition-colors",
          error
            ? "border-red-500 focus:ring-red-500"
            : "border-gray-300 dark:border-gray-600",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          className,
        ].join(" ")}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
      {helperText && !error && <p className="text-xs text-gray-500">{helperText}</p>}
    </div>
  );
}
