import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { ActivityCreate } from "../lib/types";

const dayKey = (date: string) => ["activities", date] as const;

export function useDayActivities(date: string) {
  return useQuery({
    queryKey: dayKey(date),
    queryFn: () => api.listByDate(date),
  });
}

export function useActivity(id: string | undefined) {
  return useQuery({
    queryKey: ["activity", id],
    queryFn: () => api.get(id!),
    enabled: !!id,
  });
}

/**
 * As mutações não declaram `mutationFn`: ela vem dos defaults registrados por
 * chave no queryClient. É isso que permite retomar a fila offline depois de um
 * refresh — o que fica persistido é a chave, não a função.
 */
export const useCreateActivity = () =>
  useMutation<unknown, Error, ActivityCreate>({ mutationKey: ["activity", "create"] });

export const useCompleteActivity = () =>
  useMutation<unknown, Error, string>({ mutationKey: ["activity", "complete"] });

export const usePostponeActivity = () =>
  useMutation<unknown, Error, { id: string; date: string; time: string | null }>({
    mutationKey: ["activity", "postpone"],
  });

export const useUpdateActivity = () =>
  useMutation<unknown, Error, { id: string; patch: Partial<ActivityCreate> }>({
    mutationKey: ["activity", "update"],
  });

export const useDeleteActivity = () =>
  useMutation<unknown, Error, string>({ mutationKey: ["activity", "delete"] });
