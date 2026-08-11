export type ActivityType = "task" | "call" | "meeting" | "appointment" | "reminder";
export type ActivityPriority = "high" | "attention" | "normal" | "low";
export type ActivityStatus = "pending" | "completed" | "cancelled";

export interface Activity {
  id: string;
  title: string;
  description: string | null;
  scheduled_date: string;
  scheduled_time: string | null;
  type: ActivityType;
  priority: ActivityPriority;
  status: ActivityStatus;
  reminder_at: string | null;
  reminder_sent: boolean;
  postponed_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ActivityCreate {
  title: string;
  scheduled_date: string;
  scheduled_time?: string | null;
  description?: string | null;
  type?: ActivityType;
  priority?: ActivityPriority;
  reminder_offset_min?: number | null;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  timezone: string;
  created_at: string;
}

export const PRIORITY_LABEL: Record<ActivityPriority, string> = {
  high: "Alta",
  attention: "Atenção",
  normal: "Normal",
  low: "Baixa",
};

/** Rótulo do badge nos cards: cor + texto, para não depender só da cor. */
export const PRIORITY_BADGE: Record<ActivityPriority, string> = {
  high: "URGENTE",
  attention: "ATENÇÃO",
  normal: "NORMAL",
  low: "BAIXA",
};

/** Classes do badge por prioridade (fundo translúcido + texto na cor da série). */
export const PRIORITY_BADGE_CLASS: Record<ActivityPriority, string> = {
  high: "bg-red-500/15 text-red-400",
  attention: "bg-amber-500/15 text-amber-400",
  normal: "bg-blue-500/15 text-blue-400",
  low: "bg-slate-500/15 text-slate-400",
};

/** Plural dos tipos para os contadores ("3 ligações"). */
export const TYPE_PLURAL: Record<ActivityType, [string, string]> = {
  task: ["tarefa", "tarefas"],
  call: ["ligação", "ligações"],
  meeting: ["reunião", "reuniões"],
  appointment: ["compromisso", "compromissos"],
  reminder: ["lembrete", "lembretes"],
};

export interface TypeCount {
  type: ActivityType;
  total: number;
  completed: number;
}

export interface DaySummary {
  date: string;
  total: number;
  pending: number;
}

export interface ActivityStats {
  date_from: string;
  date_to: string;
  total: number;
  completed: number;
  pending: number;
  by_type: TypeCount[];
}

export const PRIORITY_COLOR: Record<ActivityPriority, string> = {
  high: "var(--color-priority-high)",
  attention: "var(--color-priority-attention)",
  normal: "var(--color-priority-normal)",
  low: "var(--color-priority-low)",
};

export const TYPE_LABEL: Record<ActivityType, string> = {
  task: "Tarefa",
  call: "Ligação",
  meeting: "Reunião",
  appointment: "Compromisso",
  reminder: "Lembrete",
};

export const TYPE_ICON: Record<ActivityType, string> = {
  task: "✓",
  call: "📞",
  meeting: "👥",
  appointment: "📍",
  reminder: "🔔",
};
