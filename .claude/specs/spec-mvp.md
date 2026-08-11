# SPEC — Assistente de Agenda Pessoal (MVP)

*Especificação de desenvolvimento v1.0 — 10/08/2026*
*Projeto pessoal, open source. Baseada na Análise de Concepção Técnica validada.*

---

## 1. Problema e objetivo

Registrar e consultar atividades do dia precisa ser radicalmente mais simples do que em calendários tradicionais. O app entrega o loop: **abrir → ver o dia → registrar em ≤3 interações → receber lembrete → concluir**.

**Metas do MVP:**

- G1. Criar uma atividade simples em no máximo 3 interações principais (toque no `+`, digitar título, salvar).
- G2. Tela Hoje carrega em <1s (com cache) e mostra tudo do dia sem scroll em um celular comum (até ~8 itens).
- G3. Lembrete push entregue no horário (±1 min) em Android, desktop e iOS com PWA instalado.
- G4. Projeto self-hostável por terceiros com `docker compose up` + `.env` (é open source).

**Não-metas (fora do MVP):**

- Integração Google/Apple Calendar, times, compartilhamento, CRM, chat, anexos — fases futuras.
- Recorrências (nem simples) — v1.1.
- Entrada por linguagem natural / IA — v2 (arquitetura já preparada, ver §10).
- App nativo / lojas — só se a validação iOS exigir (rota Capacitor).
- Sincronização offline bidirecional — MVP tem cache de leitura + fila simples de criação.

---

## 2. Stack (decidida)

| Camada | Escolha |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| PWA | `vite-plugin-pwa` (Workbox): manifest, SW, cache, push |
| Estado/dados | TanStack Query (cache + retry + offline mutation queue) |
| Backend | FastAPI (Python 3.12) + SQLModel + Alembic (migrações) |
| Banco | PostgreSQL 16 (Supabase gerenciado em prod; Docker local) |
| Push | Web Push VAPID via `pywebpush`; scheduler APScheduler (job por minuto) |
| Auth | Magic link por e-mail (JWT próprio) — ver §7 |
| E-mail | Resend ou SMTP configurável via env (fallback de lembrete + magic link) |
| Deploy | Frontend: Cloudflare Pages/Vercel · API+scheduler: Fly.io/Railway · Licença: MIT |

Repositório monorepo:

```
agenda/
  frontend/          # React + Vite
  backend/
    app/
      api/           # routers: auth, activities, push
      core/          # config, security, deps
      models/        # SQLModel
      services/      # reminder_scheduler, webpush, mailer
    alembic/
  docker-compose.yml # postgres + backend p/ dev e self-host
  .env.example
  README.md          # setup, screenshots, guia self-host
```

---

## 3. Modelo de dados

```sql
CREATE TABLE "user" (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text UNIQUE NOT NULL,
  name        text,
  timezone    text NOT NULL DEFAULT 'America/Sao_Paulo',
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE activity_type AS ENUM ('task','call','meeting','appointment','reminder');
CREATE TYPE activity_priority AS ENUM ('high','attention','normal','low');
CREATE TYPE activity_status AS ENUM ('pending','completed','cancelled');

CREATE TABLE activity (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  title           text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  description     text,
  scheduled_date  date NOT NULL,
  scheduled_time  time,                          -- null = "durante o dia"
  type            activity_type NOT NULL DEFAULT 'task',
  priority        activity_priority NOT NULL DEFAULT 'normal',
  status          activity_status NOT NULL DEFAULT 'pending',
  reminder_at     timestamptz,                   -- UTC, calculado da TZ do usuário
  reminder_sent   boolean NOT NULL DEFAULT false,
  postponed_count int NOT NULL DEFAULT 0,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  completed_at    timestamptz
);
CREATE INDEX idx_activity_user_date ON activity(user_id, scheduled_date);
CREATE INDEX idx_activity_reminder ON activity(reminder_at)
  WHERE reminder_sent = false AND status = 'pending' AND reminder_at IS NOT NULL;

CREATE TABLE push_subscription (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  endpoint    text UNIQUE NOT NULL,
  p256dh      text NOT NULL,
  auth        text NOT NULL,
  user_agent  text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE login_token (                        -- magic links
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  token_hash  text NOT NULL,
  expires_at  timestamptz NOT NULL,               -- +15 min
  used_at     timestamptz
);
```

**Regras semânticas:**

- `Adiar` é ação, não status: muda `scheduled_date`/`scheduled_time`, incrementa `postponed_count`, recalcula `reminder_at`, reseta `reminder_sent = false`, mantém `status = 'pending'`.
- `Concluir`: `status = 'completed'`, `completed_at = now()`; lembrete pendente é cancelado (job ignora não-pending).
- `reminder_at` é sempre derivado no backend: `(scheduled_date + reminder local time)` na timezone do usuário → UTC. Recalcular em toda edição de data/hora/lembrete.

---

## 4. API (contrato)

Base: `/api/v1`. JSON. Autenticação: `Authorization: Bearer <JWT>` exceto rotas de auth. Erros: `{ "detail": str, "code": str }`.

### Auth
| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/magic-link` | body `{email}` → envia e-mail com link. Sempre 200 (não vaza existência de conta). Cria user se não existir. Rate limit 3/h por e-mail |
| POST | `/auth/verify` | body `{token}` → valida (não usado, não expirado) → `{access_token, user}`. JWT válido 30 dias |
| GET | `/auth/me` | dados do usuário |
| PATCH | `/auth/me` | atualizar `name`, `timezone` |

### Activities
| Método | Rota | Descrição |
|---|---|---|
| GET | `/activities?date=YYYY-MM-DD` | atividades do dia, ordenadas: com horário asc, depois sem horário por prioridade |
| GET | `/activities/summary?from=&to=` | contagem por dia (indicadores do calendário) |
| POST | `/activities` | criar. Obrigatório: `title`, `scheduled_date`. Demais campos com defaults (§3) |
| PATCH | `/activities/{id}` | edição parcial |
| POST | `/activities/{id}/complete` | concluir |
| POST | `/activities/{id}/postpone` | body `{scheduled_date, scheduled_time?}` — aplica regra de adiar |
| DELETE | `/activities/{id}` | remoção definitiva |

Payload de criação (exemplo):

```json
{
  "title": "Ligar para Ana",
  "scheduled_date": "2026-08-10",
  "scheduled_time": "17:00",
  "priority": "high",
  "type": "call",
  "reminder_offset_min": 0
}
```

`reminder_offset_min`: `null` = sem lembrete; `0` = no horário; `>0` = X min antes. Se `scheduled_time` é null e offset informado → 422.

### Push
| Método | Rota | Descrição |
|---|---|---|
| GET | `/push/vapid-public-key` | chave pública p/ subscribe |
| POST | `/push/subscriptions` | salvar/atualizar subscription (upsert por `endpoint`) |
| DELETE | `/push/subscriptions` | body `{endpoint}` — remover |

**Preparação p/ IA (v2, não implementar):** reservar a rota `POST /activities/parse` — receberá `{text}` e devolverá o payload de criação preenchido para confirmação do usuário. Nenhuma outra mudança de arquitetura necessária.

---

## 5. Notificações (pipeline)

**Scheduler (backend, a cada 60s):**

1. `SELECT ... FROM activity WHERE reminder_at <= now() AND reminder_sent = false AND status = 'pending' FOR UPDATE SKIP LOCKED`;
2. Para cada: enviar Web Push a **todas** as subscriptions do usuário — payload `{title, body: "HH:MM — <título>", tag: activity_id, url: "/activity/{id}"}`;
3. Marcar `reminder_sent = true` (mesmo se algum envio falhar — nunca duplicar notificação);
4. Resposta 404/410 do push service → deletar a subscription;
5. Se usuário não tem nenhuma subscription válida → enviar lembrete por **e-mail** (fallback).

**Service Worker (frontend):**

- `push` event → `showNotification` com título/corpo/tag;
- `notificationclick` → focar/abrir o app na URL da atividade, exibindo ações Concluir/Adiar.

**Fluxo de permissão (crítico, iOS):**

- Nunca pedir permissão no primeiro load. Pedir quando o usuário criar a primeira atividade **com lembrete**, via botão explícito ("Ativar lembretes") — exigência de gesto do iOS;
- No iOS sem PWA instalado: não pedir permissão; exibir banner/onboarding "Instale para receber lembretes" com passo a passo visual (Compartilhar → Adicionar à Tela de Início). Detectar via `navigator.standalone === false` + UA iOS;
- A cada abertura do app: re-verificar subscription e re-registrar se necessário (subscriptions expiram).

---

## 6. Frontend — telas e requisitos

### 6.1 Tela Hoje (rota `/`, tela inicial)
- Header: "Hoje — 10 de agosto" + acesso ao calendário e perfil.
- Lista do dia: cada item mostra horário (ou "—"), título, **barra/borda colorida de prioridade**, ícone de tipo, estado visual de concluída (riscada, no fim da lista).
- Cores de prioridade: Alta `#EF4444` · Atenção `#F59E0B` · Normal `#3B82F6` · Baixa `#9CA3AF` (tokens de tema; dark mode desde o início).
- Ações por item: swipe direita = concluir; swipe esquerda = adiar (menu: **+1h · Hoje à noite (19h) · Amanhã (mesma hora) · Escolher…**); toque = editar; remover dentro da edição (com confirmação).
- Estado vazio: mensagem amigável + CTA de criação.
- FAB `+` fixo (área de toque ≥ 48px).

### 6.2 Criação rápida (bottom sheet sobre a tela Hoje)
- Abre com campo **título já focado e teclado aberto**.
- Chips pré-selecionados: data **Hoje** (alternativas: Amanhã · Escolher), horário **—** (picker opcional), prioridade **Normal**.
- "Mais opções" (colapsado): tipo (default Tarefa), descrição, lembrete (default: no horário, se houver horário).
- Botão Salvar sempre visível. Salvar com apenas o título digitado deve funcionar → atividade "hoje, sem horário, normal, tarefa, sem lembrete".
- **Critério de aceite G1:** título + Salvar = 3 interações no total (abrir sheet, digitar, salvar).

### 6.3 Calendário (rota `/calendar`)
- Visão mensal, navegação por swipe/setas; ponto indicador nos dias com atividades (usar `/activities/summary`).
- Toque no dia → mesma lista/componente da tela Hoje para aquela data (criação já pré-preenche a data selecionada).

### 6.4 Edição (`/activity/:id`)
- Mesmos campos da criação, todos editáveis + Concluir/Cancelar/Remover. Deep-link alvo da notificação.

### 6.5 Login (`/login`)
- Campo e-mail → "Enviar link de acesso" → tela "verifique seu e-mail". Link abre `/auth/callback?token=...` → guarda JWT → redireciona para Hoje.

### 6.6 Perfil/Config (`/settings`)
- Nome, timezone (detectada via `Intl.DateTimeFormat().resolvedOptions().timeZone` no primeiro login, editável), status das notificações (ativar/testar), logout, link do repositório.

### 6.7 PWA/offline
- Manifest: nome, ícones (192/512 + maskable), `display: standalone`, theme color.
- SW: precache do shell; runtime cache network-first para `/activities` (fallback: último cache) — **abrir o app sem rede mostra o dia como visto pela última vez**.
- Mutações offline: enfileirar criação/conclusão (TanStack Query persist + retry ao reconectar). Conflitos: last-write-wins (uso pessoal — suficiente).
- Onboarding de instalação: Android usa `beforeinstallprompt`; iOS usa o guia visual (§5).

---

## 7. Autenticação e segurança

- Magic link: token aleatório 32 bytes, armazenado **hasheado** (SHA-256), expira em 15 min, uso único.
- JWT assinado (HS256, secret via env), expiração 30 dias, renovado a cada verify. Armazenar em `localStorage` (trade-off aceito para uso pessoal; documentar no README).
- Toda query de `activity`/`push_subscription` filtrada por `user_id` do token — testar isolamento entre usuários (multiusuário desde o dia 1).
- Rate limiting nas rotas de auth; CORS restrito ao domínio do frontend; HTTPS obrigatório (requisito de SW/push).
- Sem senha em lugar nenhum. Secrets (`VAPID_PRIVATE_KEY`, `JWT_SECRET`, SMTP/Resend, `DATABASE_URL`) só via env — `.env.example` completo no repo.

---

## 8. Requisitos por prioridade

**P0 — sem isso não há MVP:**
1. Auth por magic link + JWT + multiusuário isolado.
2. CRUD de Activity com defaults e regras de §3.
3. Tela Hoje completa (listar, criar em ≤3 interações, concluir, adiar, editar, remover).
4. Pipeline de lembretes fim a fim (subscription, scheduler, push, deep-link, limpeza 404/410).
5. PWA instalável (manifest + SW + cache de leitura) + onboarding de instalação iOS.
6. Fallback de lembrete por e-mail.

**P1 — logo depois de funcionar:**
7. Calendário mensal com indicadores.
8. Fila offline de mutações.
9. Dark mode / tema.
10. Atalhos de adiar refinados + ações direto na notificação (degradar para abrir o app onde não suportado).

**P2 — decisões de arquitetura já tomadas, não construir:**
11. `POST /activities/parse` (IA / linguagem natural).
12. Recorrências simples (campo futuro `recurrence_rule` — **não** criar a coluna agora).
13. Capacitor (se dados de uso iOS exigirem).

---

## 9. Critérios de aceite (críticos)

- [ ] Digitar apenas "Ligar para Ana" e Salvar → atividade hoje, sem horário, normal, tarefa — em 3 interações.
- [ ] Lembrete 17:00 (America/Sao_Paulo), app fechado, Android → notificação 17:00 ±1 min; toque abre a atividade.
- [ ] Mesmo cenário, iPhone **com PWA instalado** → notificação chega; **sem** PWA → guia de instalação + lembrete por e-mail.
- [ ] Adiar para amanhã → some de Hoje, aparece amanhã, `postponed_count`+1, lembrete reagendado.
- [ ] Concluir antes do lembrete → nenhuma notificação enviada.
- [ ] Timezone ≠ UTC na virada de DST → lembrete na hora local correta (teste unitário).
- [ ] Abrir sem rede → última versão do dia visível.
- [ ] Dois usuários → isolamento total (teste de API).
- [ ] Push service retorna 410 → subscription removida; próximo lembrete via e-mail.
- [ ] `docker compose up` + `.env` em ambiente limpo → sistema funcional.

---

## 10. Plano de construção

| Etapa | Entrega | Gate |
|---|---|---|
| **0. Spike push iOS** (~2 dias) | Página mínima + SW + endpoint de envio; testar em iPhone real com app fechado | **Push funciona instalado?** Sim → seguir. Não → reavaliar (Capacitor no MVP) |
| **1. Fundação** | Monorepo, Docker Compose, FastAPI + migrações, auth magic link, deploy básico | Login fim a fim em produção |
| **2. Núcleo** | CRUD + tela Hoje + criação rápida + edição | App utilizável (sem lembrete) — começar uso próprio aqui |
| **3. Lembretes** | Subscriptions, scheduler, push, deep-link, e-mail fallback, onboarding iOS | Critérios de notificação passando em Android + iOS + desktop |
| **4. Acabamento** | Calendário, offline queue, dark mode, ícones/manifest, README self-host | MVP publicado no GitHub |

---

## 11. Questões em aberto (não bloqueiam etapas 0-2)

1. Default de lembrete — no horário ou 10 min antes? (decidir usando o app)
2. 4 prioridades ou 3? (colapsar "Atenção" se a UI ficar poluída — mudança trivial)
3. E-mail: Resend default + SMTP genérico via env para self-host
4. Nome do projeto / identidade visual — necessário antes da etapa 4
