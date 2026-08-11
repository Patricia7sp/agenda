import { useState } from "react";

import { addDays, inOneHour, relativeDay, today, tomorrow } from "../lib/dates";
import type { Activity } from "../lib/types";
import { Sheet } from "./Sheet";

interface Props {
  activity: Activity;
  onClose: () => void;
  onPostpone: (date: string, time: string | null) => void;
}

/** Atalhos do §6.1: +1h · Hoje à noite (19h) · Amanhã (mesma hora) · Escolher… */
export function PostponeSheet({ activity, onClose, onPostpone }: Props) {
  const [custom, setCustom] = useState(false);
  const [date, setDate] = useState(addDays(activity.scheduled_date, 1));
  const [time, setTime] = useState(activity.scheduled_time?.slice(0, 5) ?? "");

  const opcoes = [
    { label: "+1 hora", date: today(), time: inOneHour() },
    { label: "Hoje à noite (19h)", date: today(), time: "19:00" },
    {
      label: `Amanhã${activity.scheduled_time ? " (mesma hora)" : ""}`,
      date: tomorrow(),
      time: activity.scheduled_time?.slice(0, 5) ?? null,
    },
  ];

  return (
    <Sheet title={`Adiar "${activity.title}"`} onClose={onClose}>
      {!custom ? (
        <div className="flex flex-col gap-2">
          {opcoes.map((o) => (
            <button
              key={o.label}
              type="button"
              onClick={() => onPostpone(o.date, o.time)}
              className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-4 text-left"
            >
              {o.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setCustom(true)}
            className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] px-4 text-left text-[var(--color-ink-muted)]"
          >
            Escolher…
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-[var(--color-ink-muted)]">
            Data
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-[var(--color-ink-muted)]">
            Horário (opcional)
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
            />
          </label>
          <p className="text-sm text-[var(--color-ink-muted)]">
            Vai para {relativeDay(date)}.
          </p>
          <button
            type="button"
            onClick={() => onPostpone(date, time || null)}
            className="min-h-12 rounded-xl bg-blue-500 font-semibold text-white"
          >
            Adiar
          </button>
        </div>
      )}
    </Sheet>
  );
}
