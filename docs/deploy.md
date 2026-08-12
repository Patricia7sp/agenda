# Colocar em produção

Objetivo: uma URL HTTPS estável para compartilhar com quem vai testar. Estável
importa — cada endereço novo obriga a reinstalar o app no iPhone e refazer a
permissão de notificação.

Arquitetura: **frontend estático** (Cloudflare Pages ou Vercel) + **API com o
scheduler** (Fly.io ou Railway) + **Postgres gerenciado** (Supabase ou Neon).
Custo: R$0 a ~US$5/mês.

O Fly.io hospeda somente a API. O frontend não é copiado para a imagem do backend;
publique `frontend/dist` separadamente e configure `VITE_API_BASE_URL` com a URL da API.

## O que só você pode fazer

Criar contas e definir segredos exige suas credenciais — eu não faço isso por
você. Os cinco passos abaixo são seus; o resto do repositório já está pronto.

1. Criar as contas (Fly.io ou Railway · Cloudflare Pages ou Vercel · Supabase ou Neon).
2. Criar o banco gerenciado e copiar a connection string.
3. Criar o OAuth Client ID do Google.
4. Definir as variáveis e secrets no painel de cada serviço.
5. Rodar `fly deploy` (ou conectar o repositório no painel).

## Login Google e PWA

A Agenda é uma aplicação web instalável (PWA). Ela não é publicada na App Store
nem na Google Play: no celular, a pessoa abre a URL HTTPS e usa **Adicionar à Tela
de Início** ou **Instalar app**. O login é feito pelo Google; o backend valida a
credencial Google e emite o JWT próprio da Agenda.

Crie no Google Cloud um OAuth Client ID do tipo **Web application** e autorize as
origens do frontend, por exemplo `https://agenda-4gh.pages.dev` e
`http://localhost:5173` para desenvolvimento. Não coloque client secret no
frontend: o `VITE_GOOGLE_CLIENT_ID` é público; a credencial recebida é validada
no backend pelo `GOOGLE_CLIENT_ID`.

## 1. Banco

Crie um Postgres no Supabase ou Neon e pegue a URI. Troque o esquema para o driver
que usamos:

```
postgresql+psycopg://usuario:senha@host:5432/postgres?sslmode=require
```

As migrações rodam sozinhas no deploy (`release_command` do [fly.toml](../backend/fly.toml)).

## 2. API (Fly.io)

```bash
cd backend
fly launch --no-deploy          # usa o fly.toml e o Dockerfile do repo
```

Gere as chaves VAPID **novas** para produção (não reaproveite as de dev):

```bash
docker compose run --rm backend python -m app.cli vapid
```

Defina os secrets:

```bash
fly secrets set \
  DATABASE_URL="postgresql+psycopg://..." \
  JWT_SECRET="$(openssl rand -base64 48)" \
  VAPID_PUBLIC_KEY="..." \
  VAPID_PRIVATE_KEY="..." \
  VAPID_SUBJECT="mailto:seu@email.com" \
  GOOGLE_CLIENT_ID="...apps.googleusercontent.com" \
  FRONTEND_URL="https://agenda.pages.dev" \
  CORS_ORIGINS="https://agenda.pages.dev" \
  ALLOWED_EMAILS="seu-email@example.com,outro@example.com"
```

```bash
fly deploy
```

Confira: `https://agenda-api.fly.dev/health` deve responder
`push_enabled: true`, `mail_enabled: true`, `scheduler_enabled: true`.
O endpoint `https://agenda-api.fly.dev/health/ready` também precisa responder
`{"status":"ready"}`; ele testa a conexão com o banco.

**Atenção ao `auto_stop_machines`.** O `fly.toml` mantém a máquina sempre de pé
de propósito: o scheduler roda dentro do processo da API, e máquina dormindo
significa lembrete não enviado. Não ligue o auto-stop para economizar.

## 3. Frontend (Cloudflare Pages)

- Diretório raiz: `frontend`
- Comando de build: `npm run build`
- Diretório de saída: `dist`
- Variável de ambiente: `VITE_API_BASE_URL=https://agenda-api.fly.dev`
- Variável de ambiente: `VITE_GOOGLE_CLIENT_ID=...apps.googleusercontent.com`

Depois do primeiro deploy, volte na API e ajuste `FRONTEND_URL` e `CORS_ORIGINS`
para o domínio real que o Pages gerou.

## 4. Antes de compartilhar — checklist

- [ ] `/health` com `push_enabled`, `mail_enabled` e `scheduler_enabled` em `true`
- [ ] `APP_ENV=prod` (a API se recusa a subir com `JWT_SECRET` fraco)
- [ ] `ALLOWED_EMAILS` contém somente os e-mails autorizados
- [ ] Login Google funcionando para cada e-mail em `ALLOWED_EMAILS`
- [ ] Instalar o app no seu iPhone pela URL de produção e ativar as notificações
- [ ] Criar uma atividade com lembrete 2 minutos à frente, fechar o app e conferir
- [ ] Abrir o app em modo avião e ver o dia carregar do cache

## 5. O que enviar para quem vai testar

A pessoa vai precisar de instruções — no iPhone, instalar não é opcional e a
opção fica escondida. Sugestão de mensagem:

> Abra este link **no Safari**: `https://…`
> Toque em **Compartilhar** (ícone do meio da barra), role a lista para baixo e
> escolha **Adicionar à Tela de Início**. Abra o app pelo ícone novo, entre com
> o Google e, em **⚙ Ajustes**, toque em **Ativar lembretes**.

O próprio app cobre esse caminho: em aba do Safari no iOS ele mostra o passo a
passo de instalação em vez de deixar a pessoa travada.

## Limites conhecidos desta versão

- **JWT no `localStorage`** — mantido para a PWA cross-domain; o cache local é apagado
  ao trocar de usuário ou sair.
- **Sem recorrências** e **sem sincronização bidirecional offline** — a fila cobre
  criação e conclusão, e conflitos resolvem por último-que-escreve.
