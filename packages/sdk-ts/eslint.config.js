import js from "@eslint/js";
import tseslint from "typescript-eslint";

// Lint the TypeScript SDK only. The game JS under src/ moves out in a later PR.
export default tseslint.config(
  { ignores: ["dist/**", "src/**/*.js"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.ts"],
    rules: { "@typescript-eslint/no-explicit-any": "warn" },
  },
);