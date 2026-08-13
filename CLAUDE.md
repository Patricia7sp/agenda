# Agenda — Assistente de Agenda Pessoal

Projeto pessoal open source (MIT): agenda + to-do + lembretes com foco em simplicidade.
Loop central: abrir → ver o dia → registrar em ≤3 interações → receber lembrete → concluir.

## Documentos-fonte (leia antes de implementar)

- `.claude/specs/spec-mvp.md` — especificação completa do MVP (DDL, API, telas, critérios de aceite, plano em 5 etapas)
- `.claude/specs/analise-concepcao.md` — análise técnica que fundamenta as decisões

## Stack

- Frontend: React 18 + Vite + TypeScript + Tailwind + `vite-plugin-pwa` + TanStack Query → `frontend/`
- Backend: FastAPI (Python 3.12) + SQLModel + Alembic → `backend/`
- Banco: PostgreSQL 16 (Docker local; Supabase em prod)
- Push: Web Push VAPID (`pywebpush`) + APScheduler (job por minuto)
- Auth: magic link por e-mail + JWT (sem senha)

## Regras importantes

- `Activity` é entidade única (não separar Event/Task/Reminder)
- Adiar é AÇÃO (muda data, incrementa `postponed_count`, volta `pending`), não status
- `reminder_at` sempre em UTC, calculado da timezone do usuário no backend
- `reminder_offset_min` persiste a antecedência escolhida; alterar ou adiar um evento deve preservá-la
- `scheduled_date` (date) e `scheduled_time` (time, nullable) separados — atividade sem horário é válida
- Toda query filtrada por `user_id` do JWT — multiusuário desde o dia 1
- Secrets só via env (`.env.example` deve estar sempre completo)
- Nunca duplicar notificação: marcar `reminder_sent` mesmo com falha parcial de envio
- `VAPID_SUBJECT` é normalizado para URI `mailto:`; falha de push nunca pode impedir o fallback por e-mail

## Plano de construção (ordem)

0. Spike push iOS (validar antes de tudo)
1. Fundação: monorepo, docker-compose, FastAPI + migrações, auth
2. Núcleo: CRUD + tela Hoje + criação rápida
3. Lembretes: subscriptions, scheduler, push, e-mail fallback
4. Acabamento: calendário, offline queue, dark mode, README self-host
