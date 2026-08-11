import { useEffect, useState } from "react";

import { enablePush, getPushState, type PushState } from "../lib/push";

const DISMISS_KEY = "agenda_push_banner_dismissed";

/**
 * Aviso na tela Hoje quando há lembretes que nunca vão chegar: sem push ativo,
 * o lembrete cai no e-mail. O botão pede a permissão dentro do gesto (iOS).
 */
export function PushBanner({ hasReminders }: { hasReminders: boolean }) {
  const [state, setState] = useState<PushState | null>(null);
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(DISMISS_KEY) === "1",
  );
  const [working, setWorking] = useState(false);

  useEffect(() => {
    getPushState().then(setState);
  }, []);

  if (!hasReminders || dismissed || !state) return null;
  // "inseguro" também some daqui: não há ação possível na tela Hoje, e a
  // explicação completa (com o endereço atual) fica nos Ajustes.
  if (state === "pronto" || state === "sem-suporte" || state === "negado" || state === "inseguro")
    return null;

  function fechar() {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  }

  async function ativar() {
    setWorking(true);
    try {
      setState(await enablePush());
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mb-3 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-3">
      {state === "precisa-instalar" ? (
        <>
          <p className="text-sm">
            Para receber lembretes no iPhone, adicione o app à tela de início:
            barra do Safari → <strong>Compartilhar</strong> → role até{" "}
            <strong>Adicionar à Tela de Início</strong> — e abra pelo ícone.
          </p>
          <button
            type="button"
            onClick={fechar}
            className="mt-2 min-h-11 text-sm text-[var(--color-ink-muted)] underline"
          >
            Agora não
          </button>
        </>
      ) : (
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm">Ative as notificações para receber seus lembretes.</p>
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={ativar}
              disabled={working}
              className="min-h-11 rounded-lg bg-blue-500 px-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              {working ? "…" : "Ativar"}
            </button>
            <button
              type="button"
              onClick={fechar}
              aria-label="Dispensar"
              className="flex size-11 items-center justify-center text-[var(--color-ink-muted)]"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
