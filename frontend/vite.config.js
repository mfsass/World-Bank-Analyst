import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyApiKey = env.WORLD_ANALYST_API_KEY || "local-dev";
  const apiUpstream = env.WORLD_ANALYST_API_UPSTREAM || "http://localhost:8080";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: apiUpstream,
          changeOrigin: true,
          headers: {
            "X-API-Key": proxyApiKey,
          },
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
    },
  };
});
