import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, setToken } from "../lib/api";
import { resetQueryCache } from "../lib/queryClient";

export function AuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [erro, setErro] = useState<string | null>(null);
  const rodou = useRef(false);

  useEffect(() => {
    // O magic link é de uso único: em StrictMode o efeito roda duas vezes e a
    // segunda chamada invalidaria o login recém-feito.
    if (rodou.current) return;
    rodou.current = true;

    const token = params.get("token");
    if (!token) {
      setErro("Link sem token.");
      return;
    }

    // Remove o token da barra antes de qualquer request ou navegação.
    window.history.replaceState(null, document.title, window.location.pathname);

    api
      .verify(token)
      .then(async ({ access_token }) => {
        resetQueryCache();
        setToken(access_token);
        // Timezone detectada no primeiro login (§6.6).
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (tz) await api.updateMe({ timezone: tz }).catch(() => undefined);
        navigate("/", { replace: true });
      })
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Falha ao autenticar"));
  }, [params, navigate]);

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 text-center">
      {erro ? (
        <>
          <p className="text-red-400">{erro}</p>
          <button
            type="button"
            onClick={() => navigate("/login", { replace: true })}
            className="mt-4 min-h-11 underline"
          >
            Pedir um link novo
          </button>
        </>
      ) : (
        <p className="text-[var(--color-ink-muted)]">Entrando…</p>
      )}
    </div>
  );
}
