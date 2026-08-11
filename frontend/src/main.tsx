import { onlineManager } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { registerSW } from "virtual:pwa-register";

import { App } from "./App";
import { persister, queryClient } from "./lib/queryClient";
import "./index.css";

// Service worker: precache do shell + push. Registrado no boot para que
// `navigator.serviceWorker.ready` esteja pronto quando o push for ativado.
registerSW({ immediate: true });

// Só em dev: permite simular queda de rede pelo console para testar a fila
// offline sem depender das ferramentas do navegador.
if (import.meta.env.DEV) {
  (window as unknown as Record<string, unknown>).__agenda = { queryClient, onlineManager };
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister, maxAge: 1000 * 60 * 60 * 24 * 7 }}
      onSuccess={() => {
        // Cache restaurado: sobe o que ficou na fila enquanto estava sem rede.
        if (onlineManager.isOnline()) void queryClient.resumePausedMutations();
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </PersistQueryClientProvider>
  </StrictMode>,
);
