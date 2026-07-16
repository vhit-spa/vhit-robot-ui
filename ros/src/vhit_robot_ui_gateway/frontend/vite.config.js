import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  base: "./",

  build: {
    outDir: resolve(__dirname, "../www"),
    emptyOutDir: true,
    sourcemap: true,
  },
});