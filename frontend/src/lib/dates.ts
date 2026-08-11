/** Datas em ISO (YYYY-MM-DD) sempre no fuso local do aparelho. */

export function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function today(): string {
  return toISODate(new Date());
}

export function tomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return toISODate(d);
}

export function addDays(iso: string, days: number): string {
  const d = fromISODate(iso);
  d.setDate(d.getDate() + days);
  return toISODate(d);
}

export function fromISODate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** "10 de agosto" */
export function longDate(iso: string): string {
  return fromISODate(iso).toLocaleDateString("pt-BR", { day: "numeric", month: "long" });
}

/** "Hoje", "Amanhã", "Ontem" ou "seg, 10 de ago" */
export function relativeDay(iso: string): string {
  if (iso === today()) return "Hoje";
  if (iso === tomorrow()) return "Amanhã";
  if (iso === addDays(today(), -1)) return "Ontem";
  return fromISODate(iso).toLocaleDateString("pt-BR", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

/** "17:00" a partir de "17:00:00" */
export function shortTime(time: string | null): string {
  return time ? time.slice(0, 5) : "—";
}

/** Horário de daqui a uma hora, arredondado para o minuto. */
export function inOneHour(): string {
  const d = new Date();
  d.setHours(d.getHours() + 1);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
