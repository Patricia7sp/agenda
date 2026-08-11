import { useRef, useState } from "react";

import { shortTime } from "../lib/dates";
import { isPendingSync } from "../lib/queryClient";
import {
  PRIORITY_BADGE,
  PRIORITY_BADGE_CLASS,
  PRIORITY_COLOR,
  TYPE_ICON,
  type Activity,
} from "../lib/types";

const SWIPE_THRESHOLD = 72;

interface Props {
  activity: Activity;
  onComplete: () => void;
  onPostpone: () => void;
  onOpen: () => void;
}

export function ActivityItem({ activity, onComplete, onPostpone, onOpen }: Props) {
  const [offset, setOffset] = useState(0);
  const startX = useRef<number | null>(null);
  const done = activity.status === "completed";
  // Criada offline e ainda na fila: não tem id no servidor, então editar,
  // concluir ou adiar levaria a um 404 quando a rede voltasse.
  const aguardando = isPendingSync(activity.id);

  // Swipe direita = concluir · swipe esquerda = adiar (§6.1). Os botões
  // continuam visíveis para funcionar no desktop e com leitor de tela.
  function onTouchStart(e: React.TouchEvent) {
    if (done || aguardando) return;
    startX.current = e.touches[0].clientX;
  }

  function onTouchMove(e: React.TouchEvent) {
    if (startX.current === null) return;
    setOffset(e.touches[0].clientX - startX.current);
  }

  function onTouchEnd() {
    if (offset > SWIPE_THRESHOLD) onComplete();
    else if (offset < -SWIPE_THRESHOLD) onPostpone();
    startX.current = null;
    setOffset(0);
  }

  return (
    <li className="relative overflow-hidden rounded-xl">
      <div className="absolute inset-0 flex items-center justify-between px-4 text-sm">
        <span className={offset > SWIPE_THRESHOLD ? "text-emerald-400" : "text-slate-600"}>
          ✓ Concluir
        </span>
        <span className={offset < -SWIPE_THRESHOLD ? "text-amber-400" : "text-slate-600"}>
          Adiar →
        </span>
      </div>

      <div
        className="relative flex items-stretch gap-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] transition-transform"
        style={{ transform: `translateX(${offset}px)` }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <span
          aria-hidden
          className="w-1.5 shrink-0 rounded-l-xl"
          style={{ background: PRIORITY_COLOR[activity.priority] }}
        />

        <button
          type="button"
          onClick={onOpen}
          disabled={aguardando}
          className="flex min-h-12 flex-1 items-center gap-3 py-3 pr-2 text-left"
        >
          <span className="w-12 shrink-0 tabular-nums text-sm text-[var(--color-ink-muted)]">
            {shortTime(activity.scheduled_time)}
          </span>
          <span className="min-w-0 flex-1">
            <span
              className={`block truncate ${done ? "text-[var(--color-ink-muted)] line-through" : ""}`}
            >
              <span aria-hidden className="mr-1.5">
                {TYPE_ICON[activity.type]}
              </span>
              {activity.title}
            </span>
            <span className="mt-0.5 flex items-center gap-2">
              {aguardando && (
                <span className="rounded bg-slate-500/15 px-1.5 py-px text-[10px] font-bold tracking-wide text-slate-300">
                  ENVIANDO
                </span>
              )}
              {/* Badge textual: prioridade legível sem depender só da cor */}
              {!done && (
                <span
                  className={`rounded px-1.5 py-px text-[10px] font-bold tracking-wide ${PRIORITY_BADGE_CLASS[activity.priority]}`}
                >
                  {PRIORITY_BADGE[activity.priority]}
                </span>
              )}
              {activity.postponed_count > 0 && (
                <span className="text-xs text-[var(--color-ink-muted)]">
                  adiada {activity.postponed_count}×
                </span>
              )}
            </span>
          </span>
        </button>

        {!done && !aguardando && (
          <div className="flex shrink-0 items-center gap-1 pr-2">
            <button
              type="button"
              onClick={onPostpone}
              aria-label={`Adiar ${activity.title}`}
              className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)] active:bg-white/5"
            >
              🕘
            </button>
            <button
              type="button"
              onClick={onComplete}
              aria-label={`Concluir ${activity.title}`}
              className="flex size-11 items-center justify-center rounded-lg text-emerald-400 active:bg-white/5"
            >
              ✓
            </button>
          </div>
        )}
      </div>
    </li>
  );
}
