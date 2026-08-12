import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { InstallAppBanner } from "../components/InstallAppBanner";
import { api, ApiError, setToken } from "../lib/api";
import { loadGoogleIdentityServices, type GoogleCredentialResponse } from "../lib/google";
import { resetQueryCache } from "../lib/queryClient";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export function Login() {
  const googleButton = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      setErro("Login com Google ainda não foi configurado neste ambiente.");
      setCarregando(false);
      return undefined;
    }

    let ativo = true;
    void loadGoogleIdentityServices()
      .then(() => {
        if (!ativo || !googleButton.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response: GoogleCredentialResponse) => void entrar(response),
          auto_select: false,
          cancel_on_tap_outside: true,
          context: "signin",
        });
        googleButton.current.replaceChildren();
        window.google.accounts.id.renderButton(googleButton.current, {
          theme: "outline",
          size: "large",
          width: 360,
          text: "continue_with",
          shape: "pill",
        });
        setCarregando(false);
      })
      .catch((error: unknown) => {
        if (!ativo) return;
        setErro(error instanceof Error ? error.message : "Falha ao carregar o Google Sign-In");
        setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, []);

  async function entrar(response: GoogleCredentialResponse) {
    setErro(null);
    setCarregando(true);
    try {
      const result = await api.loginWithGoogle(response.credential);
      resetQueryCache();
      setToken(result.access_token);
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (timezone) await api.updateMe({ timezone }).catch(() => undefined);
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(from ?? "/", { replace: true });
    } catch (error: unknown) {
      setErro(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Não consegui entrar com Google",
      );
      setCarregando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6">
      <InstallAppBanner />
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-400">Agenda</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Seu dia em uma tela.</h1>
      <p className="mt-3 text-[var(--color-ink-muted)]">
        Crie sua conta ou entre com o Google. Sem senha e sem links por e-mail.
      </p>

      <section className="mt-8 rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)]/40 p-5">
        <p className="text-sm text-[var(--color-ink-muted)]">Acesso seguro</p>
        <div ref={googleButton} className="mt-4 flex min-h-11 justify-center" />
        {carregando && !erro && (
          <p className="mt-3 text-center text-sm text-[var(--color-ink-muted)]">Carregando…</p>
        )}
        {erro && <p className="mt-3 text-sm text-red-400">{erro}</p>}
      </section>
    </div>
  );
}
