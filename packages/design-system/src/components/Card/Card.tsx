import React from "react";

export interface CardProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  footer?: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  variant?: "default" | "outlined" | "elevated";
}

const paddingClasses = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

const variantClasses = {
  default: "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700",
  outlined: "bg-transparent border border-gray-300 dark:border-gray-600",
  elevated: "bg-white dark:bg-gray-800 shadow-lg border border-transparent",
};

export function Card({
  children,
  title,
  description,
  footer,
  className = "",
  padding = "md",
  variant = "default",
}: CardProps) {
  return (
    <div className={["rounded-xl", variantClasses[variant], className].join(" ")}>
      {(title || description) && (
        <div className={["border-b border-gray-200 dark:border-gray-700", paddingClasses[padding]].join(" ")}>
          {title && <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h3>}
          {description && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>}
        </div>
      )}
      <div className={paddingClasses[padding]}>{children}</div>
      {footer && (
        <div className={["border-t border-gray-200 dark:border-gray-700", paddingClasses[padding]].join(" ")}>
          {footer}
        </div>
      )}
    </div>
  );
}
