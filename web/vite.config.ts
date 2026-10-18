/// <reference types="vitest" />
import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/",
  publicDir: "public",
  cacheDir: "node_modules/.vite",

  plugins: [
    tanstackRouter({
      quoteStyle: "double",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] }),
  ],

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    extensions: [".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"],
  },

  server: {
    port: 3000,
    host: true,
    strictPort: true,
    open: false,
    cors: false,
  },

  build: {
    outDir: "dist",
    assetsDir: "assets",
    assetsInlineLimit: 4096,
    cssCodeSplit: true,
    cssMinify: true,
    sourcemap: false,
    minify: "terser",
    terserOptions: {
      module: true,
      compress: {
        drop_console: true,
        drop_debugger: true,
        keep_classnames: false,
        keep_fnames: false,
        passes: 2,
        dead_code: true,
      },
      format: {
        comments: false,
        beautify: false,
        ascii_only: true,
      },
    },
    chunkSizeWarningLimit: 500,
    emptyOutDir: true,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/test_setup.ts"],
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reportsDirectory: "./.coverage",
      reporter: ["text", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/routeTree.gen.ts", "src/main.tsx"],
    },
  },
});
