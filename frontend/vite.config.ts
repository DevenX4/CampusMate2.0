/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser talks only to this origin; /api is forwarded to FastAPI. The session cookie is
// therefore same-origin, the backend needs no CORS, and the browser never sees PostgreSQL or
// Chroma. CAMPUSMATE_API overrides the backend address.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": process.env.CAMPUSMATE_API ?? "http://127.0.0.1:8000" },
  },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
