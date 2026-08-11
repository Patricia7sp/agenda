# Spike de push no iOS — resultado (etapa 0)

*Executado em 10/08/2026 · iPhone com iOS 18.7, Safari 26.5.2 · Encerrado.*

## Veredito

**Aprovado.** Push entregue e exibido em iPhone real com o app fechado. O projeto segue
como PWA; Capacitor fica arquivado como rota de evolução, sem necessidade no MVP.

A primeira rodada não exibiu banner por causa do **Modo Foco** ativo no aparelho — o
push era entregue e ia calado para a Central de Notificações. Com o Foco desligado, os
banners chegaram normalmente.

## O que foi provado

| Etapa | Evidência |
|---|---|
| PWA instalável via Safari | App aberto pelo ícone, `standalone` detectado |
| Push API disponível no app instalado | `SW ✓ · PushManager ✓ · Notification ✓` |
| Permissão concedida | `Permissão: granted` |
| Subscription registrada | `push_subscription` com endpoint `web.push.apple.com` |
| Envio VAPID aceito pela Apple | `sent=1 failed=0 removed=0` (HTTP 201 do push service) |
| Exibição do banner com app fechado | Banner recebido na tela bloqueada, com o app fechado |
| Notificação local (sem servidor) | Exibida — isola ajustes do iOS do pipeline de push |

## O que aprendemos (vale para a etapa 3 e para o onboarding do MVP)

1. **Em aba do Safari no iOS, `window.PushManager` e `window.Notification` não existem.**
   Checar suporte antes de checar instalação produz a mensagem errada ("navegador não
   suporta") quando a causa real é "não instalado". A ordem correta é: instalado? →
   suporte? → permissão.
2. **`Notification.requestPermission()` deve ser a primeira chamada do handler**, antes
   de qualquer `await`. A ativação transitória do gesto pode expirar durante o registro
   do service worker e o diálogo simplesmente não aparece.
3. **Achar "Adicionar à Tela de Início" é a maior fricção do fluxo** — a barra do Safari
   some ao rolar, o nome "Compartilhar" sugere enviar algo a alguém, e a opção fica
   abaixo das fileiras de pessoas e apps. Uma desenvolvedora levou três tentativas.
   Confirma o risco nº 1 da análise de concepção: **o onboarding de instalação precisa
   ser tela de primeira classe, com imagens, não um parágrafo.**
4. **Modo Foco suprime o banner sem nenhum sinal para a aplicação.** O servidor recebe
   sucesso do push service e não há como saber que o usuário não viu. Reforça o valor do
   fallback por e-mail e de não tratar "push enviado" como "usuário avisado".
5. Notificações com a mesma `tag` se substituem — dois envios seguidos geram um banner só.

## Consequências para o MVP

- Manter PWA (sem Capacitor) — nada indicou instabilidade do Web Push.
- Onboarding de instalação iOS como feature de primeira classe (P0, já previsto no §8).
- Fallback de e-mail permanece obrigatório.
- Na etapa 3, re-testar com Foco desligado antes de declarar o pipeline pronto.

## Como reabrir o spike

A página continua no repositório em `backend/app/static/spike/` e é servida em `/spike`
quando o backend sobe. Basta expor por HTTPS (`cloudflared tunnel --url http://localhost:8000`),
apontar `FRONTEND_URL`/`CORS_ORIGINS` para o túnel e repetir o fluxo do README.
A rota `/auth/callback` que redireciona para `/spike/` existe só enquanto o frontend real
não assume esse caminho.
