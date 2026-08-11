import { useEffect, useRef, useState } from "react";

import { relativeDay, today, tomorrow } from "../lib/dates";
import {
  PRIORITY_LABEL,
  TYPE_LABEL,
  type ActivityCreate,
  type ActivityPriority,
  type ActivityType,
} from "../lib/types";
import { Sheet } from "./Sheet";

interface Props {
  defaultDate: string;
  saving: boolean;
  onClose: () => void;
  onCreate: (payload: ActivityCreate) => void;
}

function Chip({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-11 rounded-full border px-4 text-sm ${
        active
          ? "border-blue-500 bg-blue-500/15 text-blue-300"
          : "border-[var(--color-border-subtle)] text-[var(--color-ink-muted)]"
      }`}
    >
      {children}
    </button>
  );
}

/**
 * Criação rápida (§6.2). Critério G1: abrir a folha, digitar o título e salvar —
 * três interações. Todo o resto tem default e fica atrás de "Mais opções".
 */
export function QuickCreateSheet({ defaultDate, saving, onClose, onCreate }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(defaultDate);
  const [time, setTime] = useState("");
  const [priority, setPriority] = useState<ActivityPriority>("normal");
  const [type, setType] = useState<ActivityType>("task");
  const [description, setDescription] = useState("");
  const [reminder, setReminder] = useState(true);
  const [more, setMore] = useState(false);
  const [customDate, setCustomDate] = useState(false);

  const outraData = date !== today() && date !== tomorrow();

  // Campo já focado com o teclado aberto — exigência do §6.2.
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || saving) return;
    onCreate({
      title: title.trim(),
      scheduled_date: date,
      scheduled_time: time || null,
      description: description.trim() || null,
      priority,
      type,
      // Lembrete só existe com horário; sem horário o backend recusaria (422).
      reminder_offset_min: time && reminder ? 0 : null,
    });
  }

  return (
    <Sheet title="Nova atividade" onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="O que precisa ser feito?"
          enterKeyHint="done"
          className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-4 text-base text-[var(--color-ink)] placeholder:text-slate-500"
        />

        <div className="flex flex-wrap gap-2">
          <Chip active={date === today() && !customDate} onClick={() => { setDate(today()); setCustomDate(false); }}>
            Hoje
          </Chip>
          <Chip active={date === tomorrow() && !customDate} onClick={() => { setDate(tomorrow()); setCustomDate(false); }}>
            Amanhã
          </Chip>
          {/* Criando a partir do calendário, a data vem pronta e não é Hoje nem
              Amanhã: o chip precisa mostrá-la, senão nada fica selecionado. */}
          <Chip active={customDate || outraData} onClick={() => setCustomDate(true)}>
            {customDate || outraData ? relativeDay(date) : "Escolher"}
          </Chip>
        </div>

        {customDate && (
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="min-h-12 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
          />
        )}

        <div className="flex items-center gap-3">
          <label className="text-sm text-[var(--color-ink-muted)]">Horário</label>
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="min-h-12 flex-1 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)]"
          />
          {time && (
            <button
              type="button"
              onClick={() => setTime("")}
              className="min-h-11 px-2 text-sm text-[var(--color-ink-muted)]"
            >
              limpar
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {(Object.keys(PRIORITY_LABEL) as ActivityPriority[]).map((p) => (
            <Chip key={p} active={priority === p} onClick={() => setPriority(p)}>
              {PRIORITY_LABEL[p]}
            </Chip>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setMore((v) => !v)}
          className="self-start text-sm text-[var(--color-ink-muted)] underline"
        >
          {more ? "Menos opções" : "Mais opções"}
        </button>

        {more && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              {(Object.keys(TYPE_LABEL) as ActivityType[]).map((t) => (
                <Chip key={t} active={type === t} onClick={() => setType(t)}>
                  {TYPE_LABEL[t]}
                </Chip>
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
          </div>
        )}

        <button
          type="submit"
          disabled={!title.trim() || saving}
          className="min-h-12 rounded-xl bg-blue-500 font-semibold text-white disabled:opacity-50"
        >
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </form>
    </Sheet>
  );
}
