import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  useActivity,
  useCompleteActivity,
  useDeleteActivity,
  useUpdateActivity,
} from "../hooks/useActivities";
import { relativeDay, today } from "../lib/dates";
import {
  PRIORITY_LABEL,
  TYPE_LABEL,
  type ActivityPriority,
  type ActivityType,
} from "../lib/types";

export function ActivityEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: activity, isPending, isError } = useActivity(id);

  const [title, setTitle] = useState("");
  const [date, setDate] = useState(today());
  const [time, setTime] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<ActivityPriority>("normal");
  const [type, setType] = useState<ActivityType>("task");
  const [reminder, setReminder] = useState(false);
  const [confirmando, setConfirmando] = useState(false);

  const update = useUpdateActivity();
  const complete = useCompleteActivity();
  const remove = useDeleteActivity();

  useEffect(() => {
    if (!activity) return;
    setTitle(activity.title);
    setDate(activity.scheduled_date);
    setTime(activity.scheduled_time?.slice(0, 5) ?? "");
    setDescription(activity.description ?? "");
    setPriority(activity.priority);
    setType(activity.type);
    setReminder(activity.reminder_at !== null);
  }, [activity]);

  if (isPending) {
    return <p className="p-6 text-center text-[var(--color-ink-muted)]">Carregando…</p>;
  }
  if (isError || !activity) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Atividade não encontrada.</p>
        <button type="button" onClick={() => navigate("/")} className="mt-4 min-h-11 underline">
          Voltar para hoje
        </button>
      </div>
    );
  }

  const voltar = () => navigate(-1);

  function salvar(e: React.FormEvent) {
    e.preventDefault();
    update.mutate(
      {
        id: activity!.id,
        patch: {
          title: title.trim(),
          scheduled_date: date,
          scheduled_time: time || null,
          description: description.trim() || null,
          priority,
          type,
          reminder_offset_min: time && reminder ? 0 : null,
        },
      },
    );
    voltar();
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-4 pb-10">
      <header className="flex items-center gap-2 pt-[calc(1rem+env(safe-area-inset-top))] pb-4">
        <button
          type="button"
          onClick={voltar}
          aria-label="Voltar"
          className="flex size-11 items-center justify-center rounded-lg text-[var(--color-ink-muted)]"
        >
          ‹
        </button>
        <h1 className="text-lg font-semibold">Editar</h1>
      </header>

      <form onSubmit={salvar} className="flex flex-col gap-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-4 text-base text-[var(--color-ink)]"
        />

        <div className="flex gap-3">
          <label className="flex flex-1 flex-col gap-1 text-sm text-[var(--color-ink-muted)]">
            Data
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
            />
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm text-[var(--color-ink-muted)]">
            Horário
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
            />
          </label>
        </div>
        <p className="-mt-2 text-sm text-[var(--color-ink-muted)]">{relativeDay(date)}</p>

        <div className="flex flex-wrap gap-2">
          {(Object.keys(PRIORITY_LABEL) as ActivityPriority[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriority(p)}
              className={`min-h-11 rounded-full border px-4 text-sm ${
                priority === p
                  ? "border-blue-500 bg-blue-500/15 text-blue-300"
                  : "border-[var(--color-border-subtle)] text-[var(--color-ink-muted)]"
              }`}
            >
              {PRIORITY_LABEL[p]}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {(Object.keys(TYPE_LABEL) as ActivityType[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setType(t)}
              className={`min-h-11 rounded-full border px-4 text-sm ${
                type === t
                  ? "border-blue-500 bg-blue-500/15 text-blue-300"
                  : "border-[var(--color-border-subtle)] text-[var(--color-ink-muted)]"
              }`}
            >
              {TYPE_LABEL[t]}
            </button>
          ))}
        </div>

        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descrição (opcional)"
          rows={3}
          className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3 text-base text-[var(--color-ink)] placeholder:text-slate-500"
        />

        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={reminder}
            disabled={!time}
            onChange={(e) => setReminder(e.target.checked)}
            className="size-5"
          />
          <span className={time ? "" : "text-[var(--color-ink-muted)]"}>
            Lembrete no horário {time ? "" : "(precisa de um horário)"}
          </span>
        </label>

        {activity.postponed_count > 0 && (
          <p className="text-sm text-[var(--color-ink-muted)]">
            Já adiada {activity.postponed_count}×.
          </p>
        )}

        <button
          type="submit"
          disabled={!title.trim() || update.isPending}
          className="min-h-12 rounded-xl bg-blue-500 font-semibold text-white disabled:opacity-50"
        >
          {update.isPending ? "Salvando…" : "Salvar"}
        </button>
      </form>

      <div className="mt-8 flex flex-col gap-2 border-t border-[var(--color-border-subtle)] pt-6">
        {activity.status === "pending" && (
          <button
            type="button"
            onClick={() => { complete.mutate(activity.id); voltar(); }}
            className="min-h-12 rounded-xl border border-emerald-500/40 text-emerald-400"
          >
            Concluir
          </button>
        )}

        {confirmando ? (
          <div className="rounded-xl border border-red-500/40 p-4">
            <p className="text-sm">Remover definitivamente?</p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => { remove.mutate(activity.id); navigate("/"); }}
                className="min-h-11 flex-1 rounded-lg bg-red-500 font-semibold text-white"
              >
                Remover
              </button>
              <button
                type="button"
                onClick={() => setConfirmando(false)}
                className="min-h-11 flex-1 rounded-lg border border-[var(--color-border-subtle)]"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmando(true)}
            className="min-h-12 rounded-xl text-red-400"
          >
            Remover
          </button>
        )}
      </div>
    </div>
  );
}
