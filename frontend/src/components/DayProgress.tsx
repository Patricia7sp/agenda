import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { TYPE_PLURAL } from "../lib/types";

interface Props {
  date: string;
}

/**
 * Resumo do dia (§ pedido de UX): "quanto tenho / quanto já fiz" numa linha,
 * contadores por tipo embaixo. Some quando o dia está vazio.
 */
export function DayProgress({ date }: Props) {
  const { data: stats } = useQuery({
    queryKey: ["stats", date],
    queryFn: () => api.stats(date, date),
  });

  if (!stats || stats.total === 0) return null;

  const pct = Math.round((stats.completed / stats.total) * 100);

  return (
    <section
      aria-label="Progresso do dia"
      className="mb-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-4 py-3"
    >
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold">
          {stats.completed} / {stats.total} concluídas
        </p>
        <p className="text-xs text-[var(--color-ink-muted)]">
          {stats.pending} pendente{stats.pending === 1 ? "" : "s"}
        </p>
      </div>

      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-black/30"
      >
        <div
          className="h-full rounded-full bg-emerald-500 transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      <p className="mt-2 text-xs text-[var(--color-ink-muted)]">
        {stats.by_type
          .map(({ type, total, completed }) => {
            const [sing, plural] = TYPE_PLURAL[type];
            const nome = total === 1 ? sing : plural;
            return completed > 0 ? `${total} ${nome} (${completed} ✓)` : `${total} ${nome}`;
          })
          .join(" · ")}
      </p>
    </section>
  );
}
