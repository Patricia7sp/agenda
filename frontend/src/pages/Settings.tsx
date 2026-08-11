import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, clearToken } from "../lib/api";
import { enablePush, getPushState, isIOS, type PushState } from "../lib/push";
import { resetQueryCache } from "../lib/queryClient";

const PUSH_LABEL: Record<PushState, string> = {
  pronto: "Ativas neste aparelho",
  inseguro: "Indisponíveis neste endereço",
  "precisa-instalar": "Falta instalar o app na tela de início",
  "sem-suporte": "Este navegador não suporta notificações",
  negado: "Bloqueadas nas configurações do sistema",
  desativado: "Desativadas",
};

/** Cada estado precisa dizer o que fazer a seguir — nunca só o diagnóstico. */
function PushHelp({ state }: { state: PushState }) {
  if (state === "inseguro") {
    return (
      <div className="mt-2 text-sm text-[var(--color-ink-muted)]">
        <p>
          Notificações exigem HTTPS. Você abriu o app por{" "}
          <strong className="text-[var(--color-ink)]">{window.location.host}</strong>, que é uma
          conexão comum — o navegador desliga o service worker e a Push API aqui.
        </p>
        <p className="mt-2">Abra o app pelo endereço <code>https://…</code> e instale por lá.</p>
      </div>
    );
  }

  if (state === "precisa-instalar") {
    return (
      <ol className="mt-2 list-decimal pl-5 text-sm text-[var(--color-ink-muted)]">
        <li>Toque em <strong>Compartilhar</strong> — o ícone do meio da barra do Safari.</li>
        <li>
          Role a lista para baixo até <strong>Adicionar à Tela de Início</strong>. Você não vai
          compartilhar com ninguém: essa folha é o menu de ações da página.
        </li>
        <li>Abra o app pelo ícone novo e entre de novo — o app instalado tem storage próprio.</li>
      </ol>
    );
  }

  if (state === "negado") {
    return (
      <p className="mt-2 text-sm text-[var(--color-ink-muted)]">
        Reative nas notificações do sistema{isIOS ? " (Ajustes → Notificações → Agenda)" : ""} e
        volte aqui para tocar em Ativar.
      </p>
    );
  }

  return null;
}

export function Settings() {
  const navigate = useNavigate();
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [push, setPush] = useState<PushState | null>(null);
  const [working, setWorking] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    getPushState().then(setPush);
  }, []);

  async function ativar() {
    setWorking(true);
    setErro(null);
    try {
      setPush(await enablePush());
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao ativar");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-4">
      <header className="flex items-center gap-2 pt-[calc(1rem+env(safe-area-inset-top))] pb-4">
        <button
          type="button"
          onClick={() => navigate("/")}
          aria-label="Voltar"
          className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
        >
          ‹
        </button>
        <h1 className="text-lg font-semibold">Ajustes</h1>
      </header>

      <dl className="rounded-xl border border-[var(--color-border-subtle)] p-4 text-sm">
        <dt className="text-[var(--color-ink-muted)]">E-mail</dt>
        <dd className="mb-3">{user?.email ?? "…"}</dd>
        <dt className="text-[var(--color-ink-muted)]">Fuso horário</dt>
        <dd>{user?.timezone ?? "…"}</dd>
      </dl>

      <section className="mt-4 rounded-xl border border-[var(--color-border-subtle)] p-4">
        <h2 className="text-sm font-semibold">Notificações</h2>
        <p className="mt-1 text-sm text-[var(--color-ink-muted)]">
          {push ? PUSH_LABEL[push] : "Verificando…"}
        </p>
        {push && <PushHelp state={push} />}

        {(push === "desativado" || push === "pronto" || push === "negado") && (
          <button
            type="button"
            onClick={ativar}
            disabled={working}
            className="mt-3 min-h-11 rounded-lg bg-blue-500 px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            {working ? "Ativando…" : push === "pronto" ? "Re-registrar aparelho" : "Ativar lembretes"}
          </button>
        )}
        {erro && <p className="mt-2 text-sm text-red-400">{erro}</p>}
        <p className="mt-3 text-xs text-[var(--color-ink-muted)]">
          Sem notificações ativas, os lembretes chegam por e-mail.
        </p>
      </section>

      <button
        type="button"
        onClick={() => {
          clearToken();
          resetQueryCache();
          navigate("/login", { replace: true });
        }}
        className="mt-8 min-h-12 rounded-xl border border-[var(--color-border-subtle)]"
      >
        Sair
      </button>
    </div>
  );
}
