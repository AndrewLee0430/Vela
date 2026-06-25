import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

// Standard Next.js 15 + ESLint 9 flat config. The repo already ships the deps for
// this (`@eslint/eslintrc` FlatCompat shim + `eslint-config-next`); only this file
// was missing, which is why `npm run lint` (bare `eslint`) errored repo-wide. See
// TECH_DEBT "ESLint flat-config migration".
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  {
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "node_modules/**",
      "next-env.d.ts",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
