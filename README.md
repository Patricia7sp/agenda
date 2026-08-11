# Agenda

Assistente de agenda pessoal — calendário + to-do + lembretes, com foco radical em simplicidade.
**Abrir → ver o dia → registrar em ≤3 interações → receber o lembrete → concluir.**

Projeto pessoal e open source (MIT).

## Estado atual

Etapas 0 e 1 concluídas. O [spike de push no iOS](docs/spike-push-ios.md) foi validado
em iPhone real e o projeto segue como PWA (sem Capacitor).

- ✅ `docker compose up` sobe Postgres + API com as migrações aplicadas
- ✅ Auth magic link + JWT, multiusuário isolado
- ✅ Registro de push subscriptions + envio VAPID + fallback de e-mail
- ✅ PWA mínima instalável em `/spike` em ambiente dev — instalação, permissão, subscription e envio
  aceito pela Apple confirmados em iPhone real
- ✅ CRUD de atividades com lembrete em UTC, adiar como ação e isolamento por usuário
- ✅ Frontend React + Vite + TS + Tailwind: login, tela Hoje, criação rápida e edição
- ✅ Lembretes ponta a ponta: scheduler por minuto, Web Push com deep-link e fallback
  por e-mail — **validado em iPhone real com o app fechado**
- ✅ Calendário mensal com indicadores de densidade
- ✅ Offline: cache de leitura persistido e fila de criações/conclusões que sobe
  sozinha ao reconectar
- ⬜ Deploy em produção — ver [guia](docs/deploy.md)

## Rodando o app

Backend (Docker) e frontend (Vite) em terminais separados:

```bash
docker compose up
```

```bash
npm install --prefix frontend && npm run dev --prefix frontend
```

O app abre em `http://localhost:5173`. O Vite faz proxy de `/api` para a API na 8000,
então não há CORS em dev. Sem provedor de e-mail configurado e com `APP_ENV=dev`,
a tela de login mostra o link "entrar direto" — é assim que você entra sem e-mail.

## Estrutura

```
agenda/
  frontend/        # React + Vite + TS + Tailwind (PWA) — etapa 2
  backend/         # FastAPI + SQLModel + Alembic
    app/static/spike/   # PWA mínima do spike de push (etapa 0)
  .claude/specs/   # especificação do MVP e análise técnica
  docs/            # documentação adicional
```

## Documentação

- [Spec do MVP](.claude/specs/spec-mvp.md)
- [Análise de concepção técnica](.claude/specs/analise-concepcao.md)
- [Resultado do spike de push no iOS](docs/spike-push-ios.md)
- [Guia de deploy em produção](docs/deploy.md)

## Setup

```bash
cp .env.example .env
docker compose up --build
```

A API sobe em `http://localhost:8000` (docs interativas em `/docs`, health em `/health`).
As migrações rodam automaticamente na subida.

Se já houver um Postgres na 5432 da sua máquina, mude `POSTGRES_PORT` no `.env` —
isso só troca a porta publicada no host; dentro do compose o backend fala com `db:5432`.

### Hot reload (opcional)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Isso monta `./backend` dentro do container e liga o `--reload`. Só funciona se o
diretório do projeto estiver no file sharing do Docker Desktop
(Settings → Resources → File sharing; por padrão só `/Users`, `/Volumes`, `/private`
e `/tmp`). Fora dessa lista o Docker monta uma pasta **vazia** sem avisar e o
container sobe quebrado — por isso o bind mount não faz parte do compose padrão.

### Gerar as chaves VAPID

Sem elas o push fica desligado (a API responde `503` em `/push/vapid-public-key`).

```bash
docker compose run --rm backend python -m app.cli vapid
```

Cole a saída no `.env` e reinicie: `docker compose up -d backend`.

### E-mail

Sem `RESEND_API_KEY` nem `SMTP_HOST`, os e-mails são apenas escritos no log. Com
`APP_ENV=dev`, o magic link também volta no corpo da resposta (`dev_magic_link`)
para você conseguir entrar sem provedor configurado. **Nunca use `APP_ENV=dev` em produção.**

## Spike de push (etapa 0) — como validar no iPhone

O gate do projeto: notificação chega com o app fechado?

### O que o iOS exige (leia antes de testar)

**Em aba do Safari, o iPhone não tem Push API.** `window.PushManager` e
`window.Notification` nem existem — a Apple só expõe essas APIs em *Home Screen web
apps*. Consequências práticas, todas esperadas e nenhuma delas é bug:

- o pedido de permissão de notificação **nunca aparece** numa aba comum;
- não há como registrar subscription, então "Enviar em 30s" não tem para onde entregar;
- por isso **instalar na tela de início não é opcional no iPhone** — é pré-requisito.

Requisitos que o spike já atende: HTTPS com certificado válido (o túnel entrega),
manifest com `display: standalone`, service worker no mesmo escopo da página, iOS 16.4+.
No Android/Chrome e no desktop nada disso é necessário: push funciona na aba comum.

### Preparação (no computador)

1. Gere as chaves VAPID e reinicie o backend.
2. Exponha a API por HTTPS (Service Worker e push exigem TLS). Ex.:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. No `.env`, adicione a URL do túnel em `CORS_ORIGINS` e aponte
   `FRONTEND_URL=https://<tunel>` (sem barra no fim). Reinicie o backend.
   Enquanto o frontend real não existe, a API redireciona `/auth/callback` para
   `/spike/`, então o magic link funciona direto — essa rota some na etapa 2.

### Teste no iPhone (a ordem importa)

| # | Passo | Obrigatório? |
|---|---|---|
| 1 | Abrir `https://<tunel>/spike/` **no Safari** | Sim — só o Safari instala web app no iOS |
| 2 | **Adicionar à Tela de Início** (ver abaixo) | **Sim no iPhone.** Não no Android/desktop |
| 3 | Fechar o Safari e abrir o app **pelo ícone** | Sim — pela aba, as APIs continuam ausentes |
| 4 | Entrar com o e-mail e "entrar direto" | Sim — o app instalado tem storage próprio, o login do Safari não vale nele |
| 5 | Tocar em **Ativar lembretes** | Sim |
| 6 | Aceitar a permissão no diálogo do iOS | Sim — negou, só reverte em Ajustes → Notificações |
| 7 | Tocar em **Enviar em 30s** | — |
| 8 | **Fechar o app** (deslizar para cima e remover da multitarefa) | Sim, é o que o teste valida |
| 9 | Esperar a notificação e tocar nela | — |

### Como instalar na Tela de Início (passo 2, em detalhe)

Esse é o passo que trava todo mundo, então vale o detalhe. Nada aqui é botão do nosso
app: é tudo interface do iOS.

**a) Ache a barra de ferramentas do Safari.** Ela fica embaixo — `‹ › ⬆️ 📖 ⧉` — mas
**some quando você rola a página para baixo**. Para trazer de volta: toque no relógio
no topo da tela, ou arraste a página para baixo, ou toque na borda inferior.
No iOS 26 em layout compacto pode não haver o ícone de Compartilhar na barra; nesse
caso toque em **⋯** e depois em Compartilhar.

**b) Toque em Compartilhar** — o **ícone do meio**, o quadrado com uma seta para cima.

**c) Você não vai compartilhar com ninguém.** Apesar do nome, essa folha é o *menu de
ações da página*. Nada é enviado a ninguém. Ela tem, de cima para baixo:

1. a prévia da página;
2. uma fileira de **pessoas** (sugestões de AirDrop) — **ignore**;
3. uma fileira de **apps** (Mensagens, WhatsApp, Mail…) — **ignore**;
4. uma **lista vertical de ações**: Copiar, Adicionar aos Favoritos, Buscar na Página,
   **Adicionar à Tela de Início**, Imprimir…

Arraste a folha para cima e role até o item **4**. É lá que está a opção.

**d) Toque em "Adicionar à Tela de Início"** → abre uma telinha com o ícone e o nome
"Agenda Spike" → toque em **Adicionar**, no canto superior direito.

**e) Feche o Safari e abra pelo ícone novo** (pode ter caído na última página da tela
de início ou na Biblioteca de Apps).

A opção existe para qualquer site e não depende de manifest nem de PWA. Se no canto
superior esquerdo da página aparecer **"Concluído"**, você está no navegador embutido de
outro app (Notas, WhatsApp) e não no Safari — ali a opção não existe. Abra o endereço
no Safari de verdade.

O próprio spike te protege desses erros: no iPhone em aba comum ele mostra o passo a
passo de instalação e recusa ativar, e os botões de envio ficam desabilitados enquanto
não houver uma subscription registrada.

Sucesso = a notificação chega em ~30s com o app fechado e o toque nela reabre o app.
Repita em Android/Chrome e no desktop (lá, direto na aba). Se o iOS falhar de forma
consistente, o plano prevê reavaliar a rota Capacitor antes da etapa 2.

## Testes

```bash
docker compose exec backend pytest
```

Os testes usam um banco separado (`agenda_test`), criado e migrado automaticamente
na primeira execução. O banco de desenvolvimento não é tocado.

## Segurança

- Sem senha em lugar nenhum: magic link (token de 32 bytes, guardado hasheado em SHA-256,
  uso único, 15 min) + JWT de 30 dias.
- Toda query é filtrada pelo `user_id` do token — multiusuário desde o dia 1.
- Secrets só via env; `.env` está no `.gitignore` e `.env.example` fica completo.
- Em produção, `ALLOWED_EMAILS` é obrigatório e o backend rejeita e-mails fora da allowlist antes de criar usuário ou token.
- O JWT é guardado em `localStorage` no cliente — trade-off aceito para uso pessoal.

## Licença

MIT
