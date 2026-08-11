import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { fromISODate, today } from "../lib/dates";
import { MONTH_LABEL, monthGrid, monthRange, WEEKDAYS } from "../lib/month";

const SWIPE_THRESHOLD = 60;

export function Calendar() {
  const navigate = useNavigate();
  const hoje = today();
  const base = fromISODate(hoje);
  const [year, setYear] = useState(base.getFullYear());
  const [month, setMonth] = useState(base.getMonth());
  const startX = useRef<number | null>(null);

  const celulas = monthGrid(year, month);
  const { from, to } = monthRange(year, month);
  const { data: dias } = useQuery({
    queryKey: ["summary", from, to],
    queryFn: () => api.summary(from, to),
  });

  const porDia = new Map((dias ?? []).map((d) => [d.date, d]));

  function mudarMes(delta: number) {
    const d = new Date(year, month + delta, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth());
  }

  return (
    <div
      className="mx-auto flex min-h-dvh max-w-md flex-col px-4"
      onTouchStart={(e) => (startX.current = e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (startX.current === null) return;
        const dx = e.changedTouches[0].clientX - startX.current;
        if (Math.abs(dx) > SWIPE_THRESHOLD) mudarMes(dx < 0 ? 1 : -1);
        startX.current = null;
      }}
    >
      <header className="flex items-center gap-1 pt-[calc(1rem+env(safe-area-inset-top))] pb-4">
        <button
          type="button"
          onClick={() => navigate("/")}
          aria-label="Voltar para hoje"
          className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
        >
          ‹
        </button>
        <h1 className="flex-1 text-lg font-semibold">{MONTH_LABEL(year, month)}</h1>
        <button
          type="button"
          onClick={() => mudarMes(-1)}
          aria-label="Mês anterior"
          className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
        >
          ‹
        </button>
        <button
          type="button"
          onClick={() => mudarMes(1)}
          aria-label="Próximo mês"
          className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
        >
          ›
        </button>
      </header>

      <div className="grid grid-cols-7 gap-1 pb-2 text-center text-xs text-[var(--color-ink-muted)]">
        {WEEKDAYS.map((d, i) => (
          <span key={i}>{d}</span>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {celulas.map((c) => {
          const resumo = porDia.get(c.iso);
          const ehHoje = c.iso === hoje;
          const temPendente = (resumo?.pending ?? 0) > 0;

          return (
            <button
              key={c.iso}
              type="button"
              onClick={() => navigate(c.iso === hoje ? "/" : `/dia/${c.iso}`)}
              aria-label={`${c.day} — ${resumo?.total ?? 0} atividade(s)`}
              className={`flex aspect-square flex-col items-center justify-center gap-1 rounded-lg text-sm ${
                ehHoje ? "bg-blue-500/20 font-semibold text-blue-300" : ""
              } ${c.inMonth ? "" : "text-slate-600"}`}
            >
              <span>{c.day}</span>
              {/* Indicador de densidade: até 3 pontos, cheio = ainda pendente */}
              <span className="flex h-1.5 items-center gap-0.5">
                {Array.from({ length: Math.min(resumo?.total ?? 0, 3) }).map((_, i) => (
                  <span
                    key={i}
                    className={`size-1 rounded-full ${
                      temPendente ? "bg-blue-400" : "bg-slate-600"
                    }`}
                  />
                ))}
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-6 text-center text-sm text-[var(--color-ink-muted)]">
        Toque num dia para ver e criar atividades nele.
      </p>
    </div>
  );
}
