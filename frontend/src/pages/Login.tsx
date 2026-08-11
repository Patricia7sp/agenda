import { useState } from "react";

import { api, ApiError } from "../lib/api";

export function Login() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [limitado, setLimitado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const r = await api.requestMagicLink(email.trim());
      // O backend monta o link com FRONTEND_URL (localhost). Reaproveitamos só o
      // token e apontamos para a origem atual, para o link funcionar também quando
      // o app é aberto pelo IP da rede ou por um túnel.
      const token = r.dev_magic_link
        ? new URL(r.dev_magic_link).searchParams.get("token")
        : null;
      setDevLink(token ? `/auth/callback?token=${encodeURIComponent(token)}` : null);
      setLimitado(r.dev_rate_limited);
      setEnviado(true);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao enviar o link");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold">Agenda</h1>
      <p className="mt-1 mb-8 text-[var(--color-ink-muted)]">
        Seu dia em uma tela. Sem senha: enviamos um link de acesso.
      </p>

      {enviado ? (
        <div className="rounded-xl border border-[var(--color-border-subtle)] p-4">
          {limitado ? (
            <>
              <p>Nenhum link novo foi gerado.</p>
              <p className="mt-1 text-sm text-[var(--color-ink-muted)]">
                Você atingiu o limite de links por hora para <strong>{email}</strong> — é a
                proteção contra spam. Espere um pouco, use o último link que recebeu, ou
                entre com outro e-mail.
              </p>
            </>
          ) : (
            <>
              <p>Verifique seu e-mail.</p>
              <p className="mt-1 text-sm text-[var(--color-ink-muted)]">
                Mandamos um link para <strong>{email}</strong>. Ele vale por 15 minutos.
              </p>
            </>
          )}
          {devLink && (
            <a href={devLink} className="mt-4 block text-blue-400 underline">
              Modo dev — entrar direto
            </a>
          )}
          <button
            type="button"
            onClick={() => setEnviado(false)}
            className="mt-4 min-h-11 text-sm text-[var(--color-ink-muted)] underline"
          >
            Usar outro e-mail
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
            autoComplete="email"
            className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-4 text-base text-[var(--color-ink)] placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={enviando}
            className="min-h-12 rounded-xl bg-blue-500 font-semibold text-white disabled:opacity-50"
          >
            {enviando ? "Enviando…" : "Enviar link de acesso"}
          </button>
          {erro && <p className="text-sm text-red-400">{erro}</p>}
        </form>
      )}
    </div>
  );
}
