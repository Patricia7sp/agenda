# Análise de Concepção Técnica — Assistente de Agenda Pessoal

*Avaliação crítica pré-specs — 10 de agosto de 2026 (validada)*

## 1. Viabilidade

Viável, com um único ponto de risco técnico real — notificações no iOS. CRUD, tela Hoje, calendário, PWA responsivo: tecnologia madura, baixo risco. O loop completo (abrir → registrar → lembrete → concluir) depende de push confiável; no iOS isso só funciona com o PWA instalado na tela inicial via Safari. Esse é o gargalo do projeto e foi prototipado antes das specs (etapa 0 do plano).

## 2. Arquitetura

SPA (React+Vite) + API REST (FastAPI) + PostgreSQL + scheduler cron simples (sem filas). Backend desacoplado desde o dia 1 para servir clientes futuros. SSR/Next.js desnecessário (app privado atrás de login).

## 3. Stack

React + Vite + TS + Tailwind + vite-plugin-pwa · FastAPI + SQLModel + pywebpush (VAPID) · Postgres (Supabase como banco gerenciado) · Magic link por e-mail · Vercel/Cloudflare Pages + Fly.io/Railway. Supabase como BaaS completo foi considerado e descartado: manteria a dev fora do Python e o scheduler menos natural.

## 4. Modelo de dados

Entidade `Activity` única (não separar Event/Task/Reminder — prematuro). Decisões-chave:
- `scheduled_date` + `scheduled_time` separados (atividade sem horário é válida);
- `reminder_at` sempre UTC, derivado da timezone do usuário (DST resolvido);
- `Postponed` NÃO é status — adiar é ação que muda a data e mantém `pending` (`postponed_count` preserva histórico). Status: pending | completed | cancelled;
- Tabela `push_subscription` separada (múltiplos dispositivos por usuário).

## 5. Notificações

Web Push (VAPID) disparado por scheduler no backend — não existe alternativa client-side confiável com app fechado. Suporte: Android/desktop OK; iOS 16.4+ somente com PWA instalado (instalação manual via Safari, sem prompt automático). Mitigações: onboarding de instalação como feature de primeira classe; fallback de lembrete por e-mail; limpeza de subscriptions 404/410; permissão pedida só após gesto e no momento certo.

## 6. Web/PWA/Mobile

PWA suficiente para o MVP. Capacitor é a rota de evolução (mesmo código → APNs confiável + lojas) se a validação iOS exigir. Distribuição direta fora da App Store é inviável fora da UE. Segunda base de código (RN/Flutter) descartada.

## 7. Riscos principais

1. 🔴 Push iOS dependente de instalação manual (mitigado por spike + onboarding + e-mail);
2. 🟠 Timezone/DST (UTC no banco + testes);
3. 🟠 Expiração silenciosa de subscriptions (re-registro a cada abertura);
4. 🟡 Escopo de offline (MVP = cache de leitura + fila simples, sem sync bidirecional);
5. 🟡 Produto: concorrentes gratuitos — a validação de UX (≤3 interações) importa mais que a técnica.

## 8. Complexidade e custo

3-6 semanas para uma pessoa; bloco mais arriscado: cadeia de notificações. Custo: R$0 a ~US$5/mês (tiers grátis + VPS pequena). Escalabilidade não é preocupação real neste desenho.

## 9. IA (futuro)

Entrada em linguagem natural entra como `POST /activities/parse` (texto → payload estruturado → confirmação do usuário) na frente da mesma API. Zero mudança de arquitetura.

## 10. Recomendação final (aplicada na spec)

Spike de push iOS antes de tudo; stack acima; Activity única com os ajustes citados; onboarding iOS e fallback e-mail como parte do MVP; specs derivadas das fases 1-4 do roadmap.
