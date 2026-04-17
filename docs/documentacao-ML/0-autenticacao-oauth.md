# Autenticação OAuth — API do Mercado Livre

Tudo que é necessário para criar o app, obter tokens e configurar webhooks.

---

## 1. Criar aplicativo no ML Developer

Acesse: **https://developers.mercadolivre.com.br/devcenter**

**Passo a passo:**
1. Login com sua conta do Mercado Livre
2. Clique em **"Criar uma aplicação"**
3. Preencha:
   - **Nome** da aplicação
   - **Descrição** (até 150 chars — aparece durante a autorização do usuário)
   - **URI de Redirect** — URL pública onde o ML vai enviar o `code` OAuth
4. Selecione os **Scopes**: marque `read`, `write` e `offline_access`
5. Em **Notificações**, insira a URL do webhook e selecione os tópicos
6. Ative as **Permissões funcionais** necessárias (ex: "Comunicação pré e pós-venda")
7. Salve

**Credenciais geradas:**
- **Client ID** (APP ID) — identificador público da aplicação
- **Client Secret** — chave privada. Nunca exponha no código ou repositório

---

## 2. Fluxo OAuth completo

### Passo 1 — Gerar o authorization code

Redirecione o usuário para a URL abaixo no navegador:

```
https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}
```

O usuário faz login e autoriza. O ML redireciona de volta para o `redirect_uri` com o code:

```
https://seuapp.com/callback?code=TG-abc123xyz
```

> O `code` expira em poucos minutos — troque por token imediatamente.

---

### Passo 2 — Trocar o code por access_token e refresh_token

```
POST https://api.mercadolibre.com/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
grant_type=authorization_code
client_id={CLIENT_ID}
client_secret={CLIENT_SECRET}
code={CODE_RECEBIDO}
redirect_uri={REDIRECT_URI}
```

**Exemplo:**
```bash
curl -X POST \
  -H "content-type: application/x-www-form-urlencoded" \
  'https://api.mercadolibre.com/oauth/token' \
  -d 'grant_type=authorization_code' \
  -d 'client_id=1234567890' \
  -d 'client_secret=abcdefghijklmnop' \
  -d 'code=TG-abc123xyz' \
  -d 'redirect_uri=https://seuapp.com/callback'
```

**Response:**
```json
{
  "access_token": "APP_USR-1234567890-abcdef-XXXX",
  "token_type": "bearer",
  "expires_in": 21600,
  "refresh_token": "TG-REFRESH_TOKEN_AQUI",
  "scope": "offline_access read write",
  "user_id": 291982050
}
```

**Salve os dois tokens:**
- `access_token` — use nas requisições API (expira em 6h)
- `refresh_token` — use para renovar o access_token (expira em 6 meses)

---

### Passo 3 — Usar o access_token nas requisições

Inclua em todas as requisições:

```
Authorization: Bearer {ACCESS_TOKEN}
```

---

### Passo 4 — Renovar o access_token quando expirar

O access_token dura **6 horas**. Quando expirar (HTTP 401), renove:

```
POST https://api.mercadolibre.com/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
grant_type=refresh_token
client_id={CLIENT_ID}
client_secret={CLIENT_SECRET}
refresh_token={REFRESH_TOKEN_ATUAL}
```

**Exemplo:**
```bash
curl -X POST \
  -H "content-type: application/x-www-form-urlencoded" \
  'https://api.mercadolibre.com/oauth/token' \
  -d 'grant_type=refresh_token' \
  -d 'client_id=1234567890' \
  -d 'client_secret=abcdefghijklmnop' \
  -d 'refresh_token=TG-REFRESH_TOKEN_AQUI'
```

**Response:**
```json
{
  "access_token": "APP_USR-1234567890-NOVO-TOKEN",
  "token_type": "bearer",
  "expires_in": 21600,
  "refresh_token": "TG-NOVO_REFRESH_TOKEN",
  "scope": "offline_access read write",
  "user_id": 291982050
}
```

> **Atenção:** O refresh_token é de **uso único** — cada renovação gera um novo.
> Sempre salve o novo refresh_token retornado. Se perder, precisa refazer o fluxo OAuth completo.

---

## 3. Regras do refresh_token

| Regra | Detalhe |
|-------|---------|
| Validade | 6 meses |
| Uso | Single-use — cada uso gera um novo |
| Expira se | Usuário troca a senha |
| Expira se | Client Secret é renovado no DevCenter |
| Expira se | Usuário revoga a autorização |
| Expira se | 4 meses sem uso |

---

## 4. Configurar webhook no ML Developer

**Onde configurar:** DevCenter → sua aplicação → seção Notificações

**Campos:**
- **Notification Callback URL** — URL pública do seu servidor (HTTPS obrigatório em produção)
- **Topics** — tópicos que deseja receber

**Tópicos disponíveis:**

| Tópico | Quando dispara |
|--------|----------------|
| `questions` | Nova pergunta feita em anúncio |
| `messages` | Nova mensagem pós-venda do comprador |
| `orders_v2` | Pedido criado ou status alterado |
| `shipments` | Envio criado ou status alterado |

**Requisitos da URL de webhook:**
- HTTPS obrigatório em produção
- Deve responder com HTTP 200 em até **500 milissegundos**
- Se não responder, o ML tenta mais até 15 vezes ao longo de ~1 hora
- Após 15 falhas, a notificação é descartada

**Notificações perdidas** ficam disponíveis por 48 horas em:
```
GET /users/{user_id}/feeds?last_seen={timestamp}
```

---

## 5. Regras do redirect_uri

- Deve ser **exatamente igual** ao registrado no DevCenter (sem barra no final, sem parâmetros extras)
- HTTPS obrigatório em produção
- Pode ser `http://localhost` apenas em desenvolvimento

**Válido:**
```
https://seuapp.railway.app/callback
```

**Inválido:**
```
https://seuapp.railway.app/callback/   ← trailing slash diferente
https://seuapp.railway.app/callback?x=1  ← parâmetro extra
```

---

## 6. Scopes

| Scope | O que permite |
|-------|---------------|
| `read` | GET em todos os endpoints |
| `write` | POST, PUT, DELETE |
| `offline_access` | Obter refresh_token para renovação automática sem novo login |

Para o sistema de pós-venda e follow-up, os três são necessários.

---

## 7. Variáveis de ambiente necessárias

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | Sim | Chave da API Anthropic (Claude) |
| `ML_CLIENT_ID` | Sim | Client ID do app no ML Developer |
| `ML_CLIENT_SECRET` | Sim | Client Secret do app no ML Developer |
| `ML_SELLER_ID` | Sim | Seu user_id como vendedor no ML |
| `ML_REDIRECT_URI` | Sim | URL do callback OAuth (ex: `https://seuapp.railway.app/callback`) |
| `ML_REFRESH_TOKEN` | Sim* | Token de renovação — obtido no primeiro OAuth |
| `ML_ACCESS_TOKEN` | Sim* | Token de acesso — gerado pelo OAuth ou refresh |
| `TELEGRAM_BOT_TOKEN` | Sim | Token do bot do Telegram |
| `TELEGRAM_CHAT_ID` | Sim | Seu chat_id no Telegram (só esse pode usar o bot) |
| `CONFIANCA_MINIMA` | Não | Threshold de confiança para auto-resposta (padrão: `0.75`) |
| `POLLING_INTERVAL_SEGUNDOS` | Não | Intervalo de polling de perguntas em segundos (padrão: `60`) |

*Precisa de `ML_REFRESH_TOKEN` **ou** `ML_ACCESS_TOKEN`. Com refresh_token o sistema renova sozinho.

---

## 8. Resumo dos endpoints

| Operação | Endpoint | Método |
|----------|----------|--------|
| Autorização do usuário | `https://auth.mercadolivre.com.br/authorization` | GET (navegador) |
| Trocar code por token | `https://api.mercadolibre.com/oauth/token` | POST |
| Renovar com refresh_token | `https://api.mercadolibre.com/oauth/token` | POST |
| Todas as chamadas API | `https://api.mercadolibre.com/{endpoint}` | GET/POST/PUT/DELETE |
