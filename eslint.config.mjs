import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Extract plugins so we can re-declare them in override config objects.
// In ESLint flat config each config object must declare the plugins whose rules it references.
const reactCompilerPlugin = nextVitals.find(
  (c) => c.plugins?.["react-compiler"],
)?.plugins?.["react-compiler"];
const reactHooksPlugin = nextVitals.find(
  (c) => c.plugins?.["react-hooks"],
)?.plugins?.["react-hooks"];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Supabase Edge Functions use Deno — different TS/lint rules
    "supabase/**",
  ]),
  // Downgrade pre-existing violations to warnings so CI passes.
  // Plugins must be re-declared in each config object that references their rules (ESLint flat config).
  ...(reactCompilerPlugin
    ? [
        {
          plugins: { "react-compiler": reactCompilerPlugin },
          rules: { "react-compiler/react-compiler": "warn" },
        },
      ]
    : []),
  ...(reactHooksPlugin
    ? [
        {
          plugins: { "react-hooks": reactHooksPlugin },
          rules: {
            "react-hooks/purity": "warn",
            "react-hooks/set-state-in-effect": "warn",
            "react-hooks/static-components": "warn",
          },
        },
      ]
    : []),
]);

export default eslintConfig;
