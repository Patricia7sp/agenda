import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ActivityItem } from "../components/ActivityItem";
import { DayProgress } from "../components/DayProgress";
import { PostponeSheet } from "../components/PostponeSheet";
import { PushBanner } from "../components/PushBanner";
import { QuickCreateSheet } from "../components/QuickCreateSheet";
import { refreshSubscription } from "../lib/push";
import {
  useCompleteActivity,
  useCreateActivity,
  useDayActivities,
  usePostponeActivity,
} from "../hooks/useActivities";
import { addDays, longDate, relativeDay, today } from "../lib/dates";
import type { Activity } from "../lib/types";

export function Today() {
  const { date: dateParam } = useParams();
  const date = dateParam ?? today();
  const navigate = useNavigate();

  const [creating, setCreating] = useState(false);
  const [postponing, setPostponing] = useState<Activity | null>(null);

  const { data: activities, isPending, isError, error, refetch } = useDayActivities(date);

  // Subscriptions expiram (§5): re-registra em silêncio a cada abertura.
  useEffect(() => {
    refreshSubscription();
  }, []);
  const create = useCreateActivity();
  const complete = useCompleteActivity();
  const postpone = usePostponeActivity();

  // Concluídas vão para o fim da lista (§6.1).
  const ordenadas = [...(activities ?? [])].sort(
    (a, b) => Number(a.status === "completed") - Number(b.status === "completed"),
  );

  function irPara(dias: number) {
    const destino = addDays(date, dias);
    navigate(destino === today() ? "/" : `/dia/${destino}`);
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="flex items-center justify-between gap-2 px-4 pt-[calc(1rem+env(safe-area-inset-top))] pb-3">
        <div>
          <h1 className="text-xl font-semibold">{relativeDay(date)}</h1>
          <p className="text-sm text-[var(--color-ink-muted)]">{longDate(date)}</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => irPara(-1)}
            aria-label="Dia anterior"
            className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
          >
            ‹
          </button>
          <button
            type="button"
            onClick={() => irPara(1)}
            aria-label="Próximo dia"
            className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
          >
            ›
          </button>
          <button
            type="button"
            onClick={() => navigate("/calendario")}
            aria-label="Calendário"
            className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
          >
            📅
          </button>
          <button
            type="button"
            onClick={() => navigate("/ajustes")}
            aria-label="Ajustes"
            className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
          >
            ⚙
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 pb-28">
        <PushBanner hasReminders={(activities ?? []).some((a) => a.reminder_at !== null)} />
        <DayProgress date={date} />
        {isPending && <p className="py-10 text-center text-[var(--color-ink-muted)]">Carregando…</p>}

        {isError && (
          <div className="py-10 text-center">
            <p className="text-red-400">Não consegui carregar: {(error as Error).message}</p>
            <button type="button" onClick={() => refetch()} className="mt-3 min-h-11 underline">
              Tentar de novo
            </button>
          </div>
        )}

        {activities?.length === 0 && (
          <div className="py-16 text-center">
            <p className="text-lg">Nada por aqui.</p>
            <p className="mt-1 text-[var(--color-ink-muted)]">
              {date === today() ? "Seu dia está livre." : "Nenhuma atividade neste dia."}
            </p>
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="mt-6 min-h-12 rounded-xl bg-blue-500 px-6 font-semibold text-white"
            >
              Criar a primeira
            </button>
          </div>
        )}

        <ul className="flex flex-col gap-2">
          {ordenadas.map((a) => (
            <ActivityItem
              key={a.id}
              activity={a}
              onComplete={() => complete.mutate(a.id)}
              onPostpone={() => setPostponing(a)}
              onOpen={() => navigate(`/atividade/${a.id}`)}
            />
          ))}
        </ul>
      </main>

      <button
        type="button"
        onClick={() => setCreating(true)}
        aria-label="Nova atividade"
        className="fixed bottom-[calc(1.5rem+env(safe-area-inset-bottom))] left-1/2 flex size-14 -translate-x-1/2 items-center justify-center rounded-full bg-blue-500 text-3xl text-white shadow-lg shadow-blue-500/25"
      >
        +
      </button>

      {creating && (
        <QuickCreateSheet
          defaultDate={date}
          saving={create.isPending}
          onClose={() => setCreating(false)}
          onCreate={(payload) => {
            // Fecha na hora: offline a mutação fica pausada na fila e o
            // onSuccess só viria quando a rede voltasse.
            create.mutate(payload);
            setCreating(false);
          }}
        />
      )}

      {postponing && (
        <PostponeSheet
          activity={postponing}
          onClose={() => setPostponing(null)}
          onPostpone={(d, t) => {
            postpone.mutate({ id: postponing.id, date: d, time: t });
            setPostponing(null);
          }}
        />
      )}
    </div>
  );
}
