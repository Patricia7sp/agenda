// Service worker do spike (etapa 0).
// Objetivo único: provar que push chega com o app fechado, e que o toque
// na notificação abre o app na URL certa.

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "Agenda", body: event.data ? event.data.text() : "" };
  }

  event.waitUntil(
    self.registration
      .showNotification(data.title || "Agenda", {
        body: data.body || "",
        tag: data.tag || "agenda",
        icon: "./icon-192.png",
        badge: "./icon-192.png",
        data: { url: data.url || "./" },
      })
      // Avisa a página (quando aberta) que o push chegou — separa "não chegou"
      // de "chegou mas o sistema não exibiu".
      .then(() => notifyClients("push recebido pelo service worker e exibido"))
      .catch((err) => notifyClients("push recebido, showNotification falhou: " + err.message))
  );
});

async function notifyClients(message) {
  const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const client of clients) client.postMessage({ type: "sw-log", message });
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "./", self.location.href).href;

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.startsWith(self.registration.scope) && "focus" in client) {
          client.navigate?.(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    })
  );
});
