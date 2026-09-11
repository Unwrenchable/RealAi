/**
 * Frontend access to @realai/design-system tokens.
 * Components can import { brand, tokens } without pulling React icons if only colors needed.
 */

// CSS-variable fallbacks (always available)
export const brand = {
  50: "#f0f4ff",
  100: "#dde7ff",
  200: "#c3d2ff",
  300: "#9db3ff",
  400: "#7b8fff",
  500: "#6366f1",
  600: "#4f46e5",
  700: "#4338ca",
  800: "#3730a3",
  900: "#312e81",
} as const;

export const semantic = {
  success: "#22c55e",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#3b82f6",
} as const;

/** Lazy re-export of package tokens when the package is linked */
export function loadDesignTokens(): Record<string, unknown> | null {
  try {
    return require("@realai/design-system/tokens") as Record<string, unknown>;
  } catch {
    return null;
  }
}
