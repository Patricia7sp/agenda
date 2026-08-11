import { toISODate } from "./dates";

export interface MonthCell {
  iso: string;
  day: number;
  inMonth: boolean;
}

export const WEEKDAYS = ["D", "S", "T", "Q", "Q", "S", "S"];

/** "Agosto de 2026" — só a inicial em maiúscula (capitalize do CSS viraria "De"). */
export const MONTH_LABEL = (year: number, month: number) => {
  const label = new Date(year, month, 1).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
};

/**
 * Grade do mês começando no domingo, completada com os dias vizinhos para
 * fechar as semanas — evita buracos no início e no fim da grade.
 */
export function monthGrid(year: number, month: number): MonthCell[] {
  const primeiro = new Date(year, month, 1);
  const inicio = new Date(year, month, 1 - primeiro.getDay());

  const celulas: MonthCell[] = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i);
    celulas.push({ iso: toISODate(d), day: d.getDate(), inMonth: d.getMonth() === month });
    // Para de crescer quando já cobriu o mês inteiro e fechou a semana.
    if (i >= 27 && d.getMonth() !== month && d.getDay() === 6) break;
  }
  return celulas;
}

export function monthRange(year: number, month: number): { from: string; to: string } {
  const celulas = monthGrid(year, month);
  return { from: celulas[0].iso, to: celulas[celulas.length - 1].iso };
}
