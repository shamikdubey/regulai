import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Code splitting for performance
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          ui: ["framer-motion", "lucide-react", "react-hot-toast"],
          query: ["@tanstack/react-query", "axios"],
          charts: ["recharts"],
        },
      },
    },
    // Increase chunk size warning limit (AI pages are large)
    chunkSizeWarningLimit: 1000,
  },
  server: {
    port: 5173,
    // Proxy API calls to backend in dev — no CORS issues
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  preview: {
    port: 4173,
  },
  // Required for BrowserRouter — serve index.html for all routes
  // In production Nginx handles this; in dev Vite handles it automatically
});
