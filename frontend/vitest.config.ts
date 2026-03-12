import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

const srcDir = fileURLToPath(new URL("./src", import.meta.url));
const setupFile = fileURLToPath(new URL("./src/test/setup.ts", import.meta.url));

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: [setupFile],
    globals: true,
  },
  resolve: {
    alias: {
      "@": srcDir,
    },
  },
});
