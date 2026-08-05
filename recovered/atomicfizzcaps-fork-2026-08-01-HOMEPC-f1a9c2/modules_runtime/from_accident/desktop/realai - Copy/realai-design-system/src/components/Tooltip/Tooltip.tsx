import React, { useState, useRef, useEffect } from "react";

export interface TooltipProps {
  content: string;
  children: React.ReactElement;
  placement?: "top" | "bottom" | "left" | "right";
  delay?: number;
}

export function Tooltip({ content, children, placement = "top", delay = 300 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutId = useRef<ReturnType<typeof setTimeout>>();

  const show = () => {
    timeoutId.current = setTimeout(() => setVisible(true), delay);
  };
  const hide = () => {
    clearTimeout(timeoutId.current);
    setVisible(false);
  };

  useEffect(() => {
    return () => clearTimeout(timeoutId.current);
  }, []);

  const placementClasses: Record<string, string> = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <span className="relative inline-flex" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {visible && (
        <span
          role="tooltip"
          className={[
            "absolute z-50 px-2 py-1 text-xs font-medium text-white bg-gray-900 rounded-md whitespace-nowrap pointer-events-none",
            "dark:bg-gray-700",
            placementClasses[placement],
          ].join(" ")}
        >
          {content}
        </span>
      )}
    </span>
  );
}
