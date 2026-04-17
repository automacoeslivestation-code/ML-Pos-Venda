# Follow-up Automático — API do Mercado Livre

Mensagens enviadas pelo seller para o comprador em eventos do pedido:
compra confirmada, produto enviado, produto entregue.

---

## Visão geral

- O seller **não pode iniciar conversa** via o endpoint padrão de mensagens (`/messages/packs/`) — resulta em 403
- Para iniciar, o endpoint correto é o **Action Guide**: `/messages/action_guide/packs/{pack_id}/option`
- O option_id `OTHER` permite texto livre (até 350 chars) — é o que usamos para follow-up
- Cada option_id tem uma **cota (cap)** por pedido — normalmente 1 mensagem por tipo
- Após o comprador responder, o seller pode usar o endpoint padrão de resposta

---

## Webhooks necessários

Ative os dois tópicos no ML Developer para receber eventos de pedidos e envios:

### Tópico `orders_v2`

Disparado quando um pedido muda de status (ex: pagamento confirmado = `paid`).

**Payload recebido:**
```json
{
  "resource": "/orders/2000016017263462",
  "user_id": 291982050,
  "topic": "orders_v2",
  "attempts": 1,
  "sent": "2026-04-16T16:20:00Z"
}
```

### Tópico `shipments`

Disparado quando o envio muda de status (ex: `shipped`, `delivered`).

**Payload recebido:**
```json
{
  "resource": "/shipments/987654321",
  "user_id": 291982050,
  "topic": "shipments",
  "attempts": 1,
  "sent": "2026-04-16T18:00:00Z"
}
```

---

## Dados do pedido (GET /orders/{order_id})

Após receber webhook de `orders_v2`, buscar o pedido para obter os dados necessários:

```
GET /orders/{order_id}
Authorization: Bearer {access_token}
```

**Campos importantes na response:**

| Campo | Descrição |
|-------|-----------|
| `id` | order_id (ID interno do pedido na API) |
| `pack_id` | ID usado nos endpoints de mensagens. Se null, usar o order_id |
| `status` | `paid`, `cancelled`, `dispatched`, `delivered` |
| `buyer.nickname` | Username do comprador no ML |
| `buyer.first_name` | Primeiro nome do comprador |
| `buyer.last_name` | Sobrenome do comprador |
| `order_items[0].item.title` | Nome do produto comprado |
| `order_items[0].item.id` | ID do produto (MLB...) |
| `shipping.id` | ID do envio (usado para buscar status de entrega) |
| `shipping.status` | Status do envio dentro do pedido |

**Response (resumida):**
```json
{
  "id": "2000016017263462",
  "pack_id": "2000012546698451",
  "status": "paid",
  "buyer": {
    "id": 441782523,
    "nickname": "COMPRADOR_TESTE",
    "first_name": "Maria",
    "last_name": "Silva"
  },
  "order_items": [
    {
      "item": {
        "id": "MLB1234567890",
        "title": "Suporte para Câmera de Segurança"
      },
      "quantity": 1,
      "unit_price": 89.90
    }
  ],
  "shipping": {
    "id": "987654321",
    "status": "not_yet_shipped"
  }
}
```

> **Nota:** O número que aparece para o comprador no ML (ex: `#2000012546698451`) é o `pack_id`,
> não o `order_id` da API. Para buscar o pedido use o `order_id`.

---

## Dados do envio (GET /shipments/{shipment_id})

Após receber webhook de `shipments`, buscar o envio para verificar o status e obter o order_id:

```
GET /shipments/{shipment_id}
Authorization: Bearer {access_token}
x-format-new: true
```

> O header `x-format-new: true` é necessário para obter o formato atualizado da resposta.

**Campos importantes na response:**

| Campo | Descrição |
|-------|-----------|
| `id` | shipment_id |
| `order_id` | order_id do pedido associado |
| `pack_id` | pack_id da conversa |
| `status` | Status atual do envio |
| `tracking.number` | Código de rastreamento |
| `tracking.url` | Link para rastreamento |
| `tracking.company` | Nome da transportadora |

**Status possíveis do envio:**

| Status | Significado |
|--------|-------------|
| `pending` | Criado, aguardando processamento |
| `handling` | Em preparação |
| `ready_to_ship` | Autorizado pela transportadora |
| `shipped` | Em trânsito |
| `delivered` | Entregue ao comprador |
| `not_delivered` | Não foi entregue |
| `cancelled` | Cancelado |

---

## Verificar cotas disponíveis antes de enviar

Antes de enviar uma mensagem proativa, verificar se ainda há cota disponível para o option_id:

```
GET /messages/action_guide/packs/{pack_id}/caps_available?tag=post_sale
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  { "option_id": "REQUEST_VARIANTS",    "cap_available": 1 },
  { "option_id": "REQUEST_BILLING_INFO","cap_available": 1 },
  { "option_id": "SEND_INVOICE_LINK",   "cap_available": 1 },
  { "option_id": "OTHER",               "cap_available": 1 }
]
```

- `cap_available >= 1` → pode enviar
- `cap_available = 0` → cota esgotada, não pode enviar

---

## Enviar mensagem proativa (Action Guide)

```
POST /messages/action_guide/packs/{pack_id}/option?tag=post_sale
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body para texto livre (follow-up):**
```json
{
  "option_id": "OTHER",
  "text": "Olá Maria! Seu pedido foi confirmado. Em breve você receberá o código de rastreamento."
}
```

> **Diferença crítica do endpoint de resposta:** Aqui **não tem** campos `from` e `to`.
> São apenas `option_id` e `text`. O sistema sabe quem é o seller pelo token.

**Response sucesso:**
```json
{
  "status": "available",
  "text": "Olá Maria! Seu pedido foi confirmado...",
  "message_id": 123456789
}
```

**Response quando mensagem foi moderada/bloqueada:**
```json
{
  "status": "moderated",
  "text": "Olá Maria!...",
  "message_moderation": {
    "status": "blocked",
    "reason": "out_of_place_language"
  }
}
```

**Response quando cota esgotada:**
```json
{
  "error": "You are not allowed to execute the option OTHER again."
}
```

---

## Todos os option_id disponíveis

| option_id | Tipo | Quando usar | Restrições |
|-----------|------|-------------|------------|
| `OTHER` | Texto livre (máx 350 chars) | Follow-up geral: compra confirmada, enviado, qualquer comunicação | ❌ Bloqueado após status `delivered` (em expansão para MLB) |
| `REQUEST_VARIANTS` | Template pré-definido | Solicitar especificações do produto (cor, tamanho, etc.) | ✅ Apenas Cross docking e Drop off — ❌ não funciona para Flex |
| `REQUEST_BILLING_INFO` | Template pré-definido | Solicitar documento de cobrança (CPF, etc.) | Disponível para todos os tipos de envio |
| `SEND_INVOICE_LINK` | Texto livre (máx 350 chars) | Enviar link de nota fiscal | Disponível para todos os tipos de envio |
| `DELIVERY_PROMISE` | Template pré-definido | Confirmar prazo de entrega | ✅ **Apenas Mercado Envios Flex** |

---

## O que NÃO é possível fazer

- ❌ Seller iniciar conversa via `POST /messages/packs/{pack_id}/sellers/{seller_id}` sem o comprador ter escrito antes (retorna 403)
- ❌ Enviar mais mensagens `OTHER` após a cota (cap = 1 por pedido)
- ❌ Enviar `OTHER` após pedido com status `delivered` em: MEC, MCO, MLM, MPE, MLU, MLC — e em breve MLB
- ❌ Usar `REQUEST_VARIANTS` em envios Flex
- ❌ Usar `DELIVERY_PROMISE` em envios que não são Flex
- ❌ Enviar mensagem em pedido cancelado

---

## Fluxo completo para follow-up

```
Webhook: orders_v2 (resource = /orders/{order_id})
  ↓
GET /orders/{order_id}
  → Extrai: pack_id, buyer.first_name, order_items[0].item.title
  ↓
POST /messages/action_guide/packs/{pack_id}/option?tag=post_sale
  → body: { "option_id": "OTHER", "text": "Mensagem de compra confirmada" }
  ↓
Webhook: shipments (resource = /shipments/{shipment_id})
  ↓
GET /shipments/{shipment_id}  [com header x-format-new: true]
  → Extrai: order_id, status
  ↓
Se status == "shipped":
  GET /orders/{order_id} → pack_id
  POST /messages/action_guide/packs/{pack_id}/option?tag=post_sale
    → body: { "option_id": "OTHER", "text": "Produto enviado..." }
  ↓
Se status == "delivered":
  ⚠️ OTHER pode estar bloqueado
  Se cap_available > 0:
    POST /messages/action_guide/packs/{pack_id}/option?tag=post_sale
      → body: { "option_id": "OTHER", "text": "Produto entregue..." }
```

---

## Depois que o comprador responde

Após o comprador responder qualquer mensagem, o seller pode usar o endpoint padrão de resposta (não precisa mais do action_guide):

```
POST /messages/packs/{pack_id}/sellers/{seller_id}?tag=post_sale
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "from": { "user_id": 291982050 },
  "to":   { "user_id": 3037675074 },
  "text": "Resposta ao comprador"
}
```

O `to.user_id` deve ser o **agent_id do Brasil: `3037675074`** (não o user_id do comprador).

---

## Limitação: cap_available

Cada pedido tem uma cota de **1 mensagem** por `option_id`. Se tentar enviar quando `cap_available = 0`, recebe erro:

```json
{ "error": "You are not allowed to execute the option OTHER again." }
```

O sistema captura esse erro via try/except e registra no log, sem travar. Para conferir antes de enviar:

```
GET /messages/action_guide/packs/{pack_id}/caps_available?tag=post_sale
```

Na prática, com 3 eventos distintos (compra, envio, entrega) e 1 cap para `OTHER`, só é possível enviar **1 mensagem proativa por pedido** — não as 3. Para os demais eventos usar `SEND_INVOICE_LINK` ou aguardar o comprador iniciar a conversa.

---

## Deduplicação

O ML não envia o mesmo webhook duas vezes para o mesmo evento em condições normais.
Porém, é recomendado manter um registro local dos eventos já processados por `order_id + evento`
para evitar reenvio em casos de retry do webhook ou reinício da aplicação.

---

## Erros comuns

| Código / Mensagem | Causa | Solução |
|-------------------|-------|---------|
| 403 | Tentativa de iniciar via `/messages/packs/` sem conversa prévia | Usar `/messages/action_guide/` |
| `"You are not allowed to execute the option OTHER again."` | Cota esgotada (cap = 0) | Não há como contornar — aguardar comprador responder |
| `"Message option not available for shipment type"` | Option_id incompatível com o tipo de envio | Ex: REQUEST_VARIANTS não funciona em Flex |
| 401 | Token expirado | Renovar via refresh_token |
| 429 | Rate limit (500 req/min) | Backoff exponencial |

---

## Rate limit

- **500 requisições por minuto** para GET e POST (pool compartilhado)
- Implementar backoff exponencial ao receber 429

---

## Permissão necessária no ML Developer

No painel do ML Developer → sua aplicação → Permissões funcionais:

- **"Comunicação pré e pós-venda"** com acesso de **leitura e escrita**

Sem essa permissão, os endpoints de action_guide retornam 403.
