/**
 * Registro de Web Push. A ordem das checagens vem do spike da etapa 0:
 * em aba do Safari no iOS, `PushManager` e `Notification` nem existem, então
 * checar suporte antes de checar instalação daria a mensagem errada.
 */

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;

export const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

export const isStandalone = () =>
  (window.navigator as { standalone?: boolean }).standalone === true ||
  window.matchMedia("(display-mode: standalone)").matches;

export type PushState =
  | "pronto" // subscription ativa
  | "inseguro" // aberto por HTTP: service worker e push não existem fora de HTTPS
  | "precisa-instalar" // iOS em aba: só funciona instalado na tela de início
  | "sem-suporte" // navegador sem Push API
  | "negado" // usuário negou a permissão
  | "desativado"; // suportado, mas ainda não ativado

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("agenda_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function urlB64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(normalized);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export async function getPushState(): Promise<PushState> {
  // Contexto inseguro vem primeiro: por HTTP nada de push existe, e sem essa
  // checagem o app diria "navegador sem suporte" — diagnóstico errado, sem saída.
  if (!window.isSecureContext) return "inseguro";
  if (isIOS && !isStandalone()) return "precisa-instalar";
  if (!("serviceWorker" in navigator)) return "sem-suporte";
  if (typeof Notification === "undefined" || !("PushManager" in window)) return "sem-suporte";
  if (Notification.permission === "denied") return "negado";

  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  return sub ? "pronto" : "desativado";
}

/** Precisa ser chamado a partir de um gesto do usuário (exigência do iOS). */
export async function enablePush(): Promise<PushState> {
  const estado = await getPushState();
  if (estado === "precisa-instalar" || estado === "sem-suporte" || estado === "inseguro")
    return estado;

  // Permissão ANTES de qualquer await pesado: no iOS a ativação transitória do
  // gesto expira durante o registro do service worker e o diálogo não aparece.
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "negado";

  // O service worker é registrado no boot (main.tsx); aqui só esperamos ficar pronto.
  const reg = await navigator.serviceWorker.ready;

  const keyRes = await fetch(`${BASE}/push/vapid-public-key`, { headers: authHeaders() });
  if (!keyRes.ok) throw new Error("Servidor sem chave VAPID configurada");
  const { public_key } = (await keyRes.json()) as { public_key: string };

  const existente = await reg.pushManager.getSubscription();
  const sub =
    existente ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlB64ToUint8Array(public_key),
    }));

  const json = sub.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
  const res = await fetch(`${BASE}/push/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: json.keys,
      user_agent: navigator.userAgent,
    }),
  });
  if (!res.ok) throw new Error("Não consegui registrar o dispositivo no servidor");

  return "pronto";
}

/**
 * Subscriptions expiram em silêncio (§5) — e o registro no servidor também pode
 * sumir (troca de banco, limpeza, restauração de backup). Por isso re-enviamos a
 * subscription a cada abertura do app, mesmo quando ela existe localmente: o
 * upsert por endpoint é idempotente e cura o caso "ativa no aparelho, ausente no
 * servidor", que de outra forma falharia em silêncio na hora do lembrete.
 */
export async function refreshSubscription(): Promise<void> {
  const estado = await getPushState();
  if (estado !== "desativado" && estado !== "pronto") return;
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  await enablePush().catch(() => undefined);
}
