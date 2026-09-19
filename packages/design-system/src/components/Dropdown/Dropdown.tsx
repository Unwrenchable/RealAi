import React, { useState, useRef, useEffect } from "react";

export interface DropdownItem {
  label: string;
  value: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  separator?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  onSelect?: (value: string) => void;
  placement?: "bottom-left" | "bottom-right";
  className?: string;
}

export function Dropdown({ trigger, items, onSelect, placement = "bottom-left", className = "" }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const placementClass = placement === "bottom-right" ? "right-0" : "left-0";

  return (
    <div ref={ref} className={["relative inline-flex", className].join(" ")}>
      <div onClick={() => setOpen((o) => !o)} className="cursor-pointer">
        {trigger}
      </div>
      {open && (
        <div
          className={[
            "absolute z-50 mt-1 top-full min-w-[160px] bg-white dark:bg-gray-800 rounded-lg shadow-lg",
            "border border-gray-200 dark:border-gray-700 py-1",
            placementClass,
          ].join(" ")}
        >
          {items.map((item, i) =>
            item.separator ? (
              <hr key={i} className="my-1 border-gray-200 dark:border-gray-700" />
            ) : (
              <button
                key={item.value}
                disabled={item.disabled}
                onClick={() => {
                  if (!item.disabled) {
                    onSelect?.(item.value);
                    setOpen(false);
                  }
                }}
                className={[
                  "w-full text-left flex items-center gap-2 px-3 py-2 text-sm",
                  "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700",
                  "transition-colors",
                  item.disabled ? "opacity-40 cursor-not-allowed" : "",
                ].join(" ")}
              >
                {item.icon}
                {item.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
