import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";

const sourceRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_API_PROXY_TARGET?.trim();
  const devPort = Number(env.VITE_DEV_PORT || "5173");

  return {
    root: sourceRoot,
    publicDir: false,
    plugins: [vue()],
    resolve: {
      alias: {
        "@": sourceRoot,
      },
    },
    server: {
      host: "127.0.0.1",
      port: Number.isFinite(devPort) && devPort > 0 ? devPort : 5173,
      proxy: proxyTarget
        ? {
            "/api/v1": {
              target: proxyTarget,
              changeOrigin: true,
              secure: false,
            },
          }
        : undefined,
    },
    build: {
      outDir: fileURLToPath(new URL("../dist", import.meta.url)),
      emptyOutDir: true,
    },
  };
});
