export const REMINDER_OPTIONS = [
  { value: "", label: "Sem lembrete" },
  { value: "0", label: "No horário" },
  { value: "20", label: "20 minutos antes" },
  { value: "30", label: "30 minutos antes" },
  { value: "60", label: "1 hora antes" },
] as const;

interface Props {
  disabled: boolean;
  value: number | null;
  onChange: (value: number | null) => void;
}

export function ReminderOffsetField({ disabled, value, onChange }: Props) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-[var(--color-ink-muted)]">
      Lembrar-me
      <select
        value={value ?? ""}
        disabled={disabled}
        onChange={(event) => {
          const next = event.target.value;
          onChange(next === "" ? null : Number(next));
        }}
        className="min-h-12 w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] px-3 text-base text-[var(--color-ink)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {REMINDER_OPTIONS.map((option) => (
          <option key={option.value || "none"} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {disabled && <span>Defina um horário para ativar o lembrete.</span>}
    </label>
  );
}
