import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:3000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:3000", ws: true },
      "/static": { target: "http://127.0.0.1:3000", changeOrigin: true },
      "/assets": { target: "http://127.0.0.1:3000", changeOrigin: true },
      "/output": { target: "http://127.0.0.1:3000", changeOrigin: true },
      "/generate": { target: "http://127.0.0.1:3000", changeOrigin: true },
    },
  },
});
