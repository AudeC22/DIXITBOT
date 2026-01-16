import { defineConfig } from "vite";

export default defineConfig({
  server: {
    proxy: {
      "/api": "http://127.0.0.1:51234", // Proxy pour les appels API
    },
  },
});
