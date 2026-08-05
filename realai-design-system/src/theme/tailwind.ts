import type { Config } from "tailwindcss";
import { colors } from "./tokens";

export const tailwindExtension: Partial<Config["theme"]> = {
  extend: {
    colors: {
      realai: colors.primary,
    },
    fontFamily: {
      sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      mono: ["JetBrains Mono", "Fira Code", "monospace"],
    },
  },
};
