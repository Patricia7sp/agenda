import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      // O service worker é nosso (push + deep-link); o Workbox só injeta o
      // precache do shell no build.
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      injectRegister: null, // registramos manualmente, junto com o push
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,png,svg,webmanifest}"],
      },
      devOptions: { enabled: true, type: "module" },
      manifest: {
        name: "Agenda",
        short_name: "Agenda",
        description: "Seu dia em uma tela: agenda, tarefas e lembretes.",
        start_url: "/",
        id: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        prefer_related_applications: false,
        background_color: "#0f172a",
        theme_color: "#0f172a",
        lang: "pt-BR",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    // Escuta em todas as interfaces para dar para abrir do celular na mesma rede
    // (no aparelho, "localhost" seria o próprio aparelho).
    host: true,
    // Libera o Host de túneis HTTPS (cloudflared/ngrok) usados para testar no
    // iPhone — sem isso o Vite recusa requisições com Host desconhecido.
    // Só afeta o servidor de desenvolvimento.
    allowedHosts: true,
    proxy: {
      // Em dev o frontend fala com a API pelo mesmo host, sem CORS.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
