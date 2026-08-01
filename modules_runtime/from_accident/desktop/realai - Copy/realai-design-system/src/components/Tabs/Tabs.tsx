import React, { useState } from "react";

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  defaultTab?: string;
  onChange?: (id: string) => void;
  className?: string;
  variant?: "line" | "pills";
}

export function Tabs({ items, defaultTab, onChange, className = "", variant = "line" }: TabsProps) {
  const [active, setActive] = useState(defaultTab ?? items[0]?.id);

  const handleSelect = (id: string) => {
    setActive(id);
    onChange?.(id);
  };

  const activeItem = items.find((i) => i.id === active);

  return (
    <div className={className}>
      <div
        role="tablist"
        className={[
          "flex gap-1",
          variant === "line"
            ? "border-b border-gray-200 dark:border-gray-700"
            : "bg-gray-100 dark:bg-gray-800 rounded-lg p-1",
        ].join(" ")}
      >
        {items.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={active === item.id}
            aria-controls={`tabpanel-${item.id}`}
            disabled={item.disabled}
            onClick={() => !item.disabled && handleSelect(item.id)}
            className={[
              "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors rounded-t",
              "focus:outline-none focus:ring-2 focus:ring-indigo-500",
              item.disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer",
              variant === "line"
                ? active === item.id
                  ? "border-b-2 border-indigo-600 text-indigo-600 -mb-px"
                  : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                : active === item.id
                ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm rounded-md"
                : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
            ].join(" ")}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
      <div
        id={`tabpanel-${active}`}
        role="tabpanel"
        aria-labelledby={`tab-${active}`}
        className="mt-4"
      >
        {activeItem?.content}
      </div>
    </div>
  );
}
