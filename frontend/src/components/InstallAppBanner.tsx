import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISSED_KEY = "agenda_install_banner_dismissed";

function isStandalone(): boolean {
  return (
    (window.navigator as { standalone?: boolean }).standalone === true ||
    window.matchMedia("(display-mode: standalone)").matches
  );
}

function isIOS(): boolean {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

export function InstallAppBanner() {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (isStandalone() || localStorage.getItem(DISMISSED_KEY) === "1") return undefined;

    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  const canInstall = installEvent !== null;
  if (!canInstall && !isIOS()) return null;

  function dismiss() {
    localStorage.setItem(DISMISSED_KEY, "1");
    setOpen(false);
    setInstallEvent(null);
  }

  async function install() {
    if (!installEvent) {
      setOpen(true);
      return;
    }
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === "accepted") dismiss();
    else setInstallEvent(null);
  }

  return (
    <aside className="mb-6 rounded-2xl border border-blue-400/25 bg-blue-500/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Use como app</p>
          <p className="mt-1 text-sm text-[var(--color-ink-muted)]">
            Adicione a Agenda à tela de início para abrir em uma janela própria.
          </p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Fechar instrução de instalação"
          className="size-8 text-xl leading-none text-[var(--color-ink-muted)]"
        >
          ×
        </button>
      </div>
      <button
        type="button"
        onClick={() => void install()}
        className="mt-3 min-h-11 rounded-lg bg-blue-500 px-4 text-sm font-semibold text-white"
      >
        {canInstall ? "Instalar app" : "Como adicionar"}
      </button>
      {open && (
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-[var(--color-ink-muted)]">
          <li>Toque em Compartilhar no Safari.</li>
          <li>Escolha Adicionar à Tela de Início.</li>
          <li>Abra a Agenda pelo novo ícone.</li>
        </ol>
      )}
    </aside>
  );
}
