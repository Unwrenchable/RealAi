import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

/** Flat ESLint config for the TanStack Start app-builder template. */
export default tseslint.config(
  {
    ignores: [
      "dist/**",
      ".output/**",
      ".vercel/**",
      ".nitro/**",
      "node_modules/**",
      "src/routeTree.gen.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js,jsx,mjs,cjs}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  // Ban Better Auth plugins behind Dependabot criticals (OAuth-state account
  // takeover). Also enforced in CI by scripts/check-auth-plugins.mjs and at
  // startup by src/lib/auth/plugin-guard.ts.
  {
    files: ["**/*.{ts,tsx,js,jsx,mjs,cjs}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            { name: "better-auth/plugins", importNames: ["magicLink", "oAuthProxy"], message: "magic-link / oauth-proxy are banned (security)." },
            { name: "better-auth/client/plugins", importNames: ["magicLinkClient"], message: "magic-link is banned (security)." },
          ],
          patterns: [
            { group: ["better-auth/plugins/magic-link", "better-auth/plugins/magic-link/*", "better-auth/plugins/oauth-proxy", "better-auth/plugins/oauth-proxy/*"], message: "magic-link / oauth-proxy are banned (security)." },
          ],
        },
      ],
    },
  },
  // Disable rules that conflict with Prettier formatting.
  prettier,
);
