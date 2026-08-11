import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { MutationCache, QueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Activity, ActivityCreate } from "./types";

/** Id temporário de uma atividade criada offline, ainda não confirmada pelo servidor. */
export const TEMP_PREFIX = "temp-";
export const isPendingSync = (id: string) => id.startsWith(TEMP_PREFIX);

const dayKey = (date: string) => ["activities", date] as const;

export const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    // Toda mutação bem-sucedida invalida o dia, o resumo e os indicadores.
    onSuccess: (data) => {
      const activity = data as Activity | undefined;
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      if (activity?.id) queryClient.invalidateQueries({ queryKey: ["activity", activity.id] });
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 1000 * 60 * 60 * 24 * 7, // precisa sobreviver para o cache persistido servir offline
      // Sem rede, serve o cache em vez de ficar pendurado (§6.7).
      networkMode: "offlineFirst",
      retry: (count, error) =>
        !(error instanceof Error && "status" in error && error.status === 401) && count < 2,
    },
    mutations: {
      // Offline, a mutação fica pausada na fila em vez de falhar.
      networkMode: "offlineFirst",
      retry: 2,
    },
  },
});

/**
 * Defaults por chave: é isso que permite retomar mutações que ficaram pausadas
 * antes de um refresh — a fila persistida guarda a chave, não a função.
 */
queryClient.setMutationDefaults(["activity", "create"], {
  mutationFn: (payload) => api.create(payload as unknown as ActivityCreate),
  onMutate: async (variables) => {
    const payload = variables as unknown as ActivityCreate;
    const key = dayKey(payload.scheduled_date);
    await queryClient.cancelQueries({ queryKey: key });
    const anterior = queryClient.getQueryData<Activity[]>(key);

    // Aparece na lista na hora, mesmo sem rede.
    const agora = new Date().toISOString();
    const otimista: Activity = {
      id: `${TEMP_PREFIX}${crypto.randomUUID()}`,
      title: payload.title,
      description: payload.description ?? null,
      scheduled_date: payload.scheduled_date,
      scheduled_time: payload.scheduled_time ?? null,
      type: payload.type ?? "task",
      priority: payload.priority ?? "normal",
      status: "pending",
      reminder_at: null,
      reminder_sent: false,
      postponed_count: 0,
      created_at: agora,
      updated_at: agora,
      completed_at: null,
    };
    queryClient.setQueryData<Activity[]>(key, [...(anterior ?? []), otimista]);
    return { key, anterior };
  },
  onError: (_error, _variables, context) => {
    const ctx = context as { key: readonly unknown[]; anterior?: Activity[] } | undefined;
    if (ctx?.anterior) queryClient.setQueryData(ctx.key, ctx.anterior);
  },
});

queryClient.setMutationDefaults(["activity", "update"], {
  mutationFn: (vars) => {
    const { id, patch } = vars as unknown as { id: string; patch: Partial<ActivityCreate> };
    return api.update(id, patch);
  },
});

queryClient.setMutationDefaults(["activity", "complete"], {
  mutationFn: (id) => api.complete(id as unknown as string),
  onMutate: async (variables) => {
    // Riscar na hora é o feedback esperado; sem rede a chamada fica na fila.
    const id = variables as unknown as string;
    queryClient.setQueriesData<Activity[]>({ queryKey: ["activities"] }, (lista) =>
      lista?.map((a) => (a.id === id ? { ...a, status: "completed" as const } : a)),
    );
  },
});

queryClient.setMutationDefaults(["activity", "postpone"], {
  mutationFn: (vars) => {
    const { id, date, time } = vars as unknown as { id: string; date: string; time: string | null };
    return api.postpone(id, date, time);
  },
});

queryClient.setMutationDefaults(["activity", "delete"], {
  mutationFn: (id) => api.remove(id as unknown as string),
  onMutate: async (variables) => {
    const id = variables as unknown as string;
    queryClient.setQueriesData<Activity[]>({ queryKey: ["activities"] }, (lista) =>
      lista?.filter((a) => a.id !== id),
    );
  },
});

export const persister = createSyncStoragePersister({
  storage: window.localStorage,
  key: "agenda_cache",
  throttleTime: 1000,
});

export function resetQueryCache(): void {
  queryClient.clear();
  window.localStorage.removeItem("agenda_cache");
}
