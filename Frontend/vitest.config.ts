import { defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

/**
 * Vitest hereda el plugin React de Vite para transformar JSX en tests
 * (evita `React is not defined` con `@jsxImportSource react` / TSX).
 */
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "node",
      include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    },
  })
);
