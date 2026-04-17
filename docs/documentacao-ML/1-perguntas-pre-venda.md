# Perguntas Pré-Venda — API do Mercado Livre

Compradores que ainda não compraram podem fazer perguntas diretamente no anúncio.
Este documento cobre como listar, buscar e responder essas perguntas via API.

---

## Visão geral

- Perguntas são feitas no anúncio, antes da compra
- Apenas o seller dono do item pode responder
- Limite de 2000 caracteres por resposta
- Webhook disponível para receber em tempo real

---

## Webhook

**Tópico a ativar no ML Developer:** `questions`

**Payload recebido:**
```json
{
  "resource": "/questions/3957150025",
  "user_id": 123456789,
  "topic": "questions",
  "application_id": 2069392825111111,
  "attempts": 1,
  "sent": "2024-02-06T13:44:33.006Z"
}
```

- O campo `resource` contém o ID da pergunta
- O webhook dispara quando uma nova pergunta é feita
- Após receber, faça GET na pergunta para obter os detalhes

---

## Endpoints

### Listar perguntas sem resposta

```
GET /questions/search
Authorization: Bearer {access_token}
```

**Parâmetros:**

| Parâmetro | Obrigatório | Descrição |
|-----------|-------------|-----------|
| `seller_id` | Sim | ID do seller |
| `status` | Não | `UNANSWERED` para filtrar sem resposta |
| `api_version` | Não | `4` para incluir nome/email/telefone do comprador |
| `limit` | Não | Resultados por página (padrão 50) |
| `offset` | Não | Para paginação |

**Request:**
```bash
curl -X GET \
  -H 'Authorization: Bearer $ACCESS_TOKEN' \
  'https://api.mercadolibre.com/questions/search?seller_id=291982050&status=UNANSWERED'
```

**Response:**
```json
{
  "total": 3,
  "limit": 50,
  "questions": [
    {
      "id": 3957150025,
      "seller_id": 291982050,
      "text": "Esse produto serve para câmera de 2MP?",
      "status": "UNANSWERED",
      "item_id": "MLB1234567890",
      "date_created": "2024-02-05T22:13:53.000-04:00",
      "hold": false,
      "deleted_from_listing": false,
      "from": {
        "id": 441782523
      }
    }
  ]
}
```

---

### Buscar pergunta específica por ID

```
GET /questions/{question_id}
Authorization: Bearer {access_token}
```

**Com api_version=4** retorna nome, email e telefone do comprador:

```bash
curl -X GET \
  -H 'Authorization: Bearer $ACCESS_TOKEN' \
  'https://api.mercadolibre.com/questions/3957150025?api_version=4'
```

**Response:**
```json
{
  "id": 3957150025,
  "seller_id": 291982050,
  "item_id": "MLB1234567890",
  "text": "Esse produto serve para câmera de 2MP?",
  "status": "UNANSWERED",
  "date_created": "2024-02-05T22:13:53.000-04:00",
  "hold": false,
  "deleted_from_listing": false,
  "from": {
    "id": 441782523,
    "name": "Maria Silva",
    "email": "maria@email.com",
    "phone": "11999887766"
  },
  "answer": null
}
```

**Campos do objeto `from`:**

| Campo | Existe sem api_version=4 | Existe com api_version=4 |
|-------|--------------------------|--------------------------|
| `id` | ✅ | ✅ |
| `name` | ❌ | ✅ |
| `email` | ❌ | ✅ |
| `phone` | ❌ | ✅ |
| `nickname` | ❌ | ❌ (não existe) |

> **Importante:** `from.nickname` não existe na API de perguntas. Use `from.id`.

---

### Responder uma pergunta

```
POST /answers
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body:**
```json
{
  "question_id": 3957150025,
  "text": "Sim, este produto é compatível com câmeras de até 4MP."
}
```

**Regras:**
- Máximo **2000 caracteres** por resposta
- Apenas o seller dono do item pode responder
- Não é possível editar uma resposta após postada

**Response (201 Created):**
```json
{
  "id": 3957150025,
  "status": "ANSWERED",
  "answer": {
    "text": "Sim, este produto é compatível com câmeras de até 4MP.",
    "status": "ACTIVE",
    "date_created": "2024-02-06T10:30:00.000-04:00"
  }
}
```

---

## Status possíveis de uma pergunta

| Status | Descrição |
|--------|-----------|
| `UNANSWERED` | Sem resposta, aguardando |
| `ANSWERED` | Respondida pelo seller |
| `CLOSED_UNANSWERED` | Prazo expirou sem resposta |
| `UNDER_REVIEW` | Em análise pela moderação |
| `BANNED` | Bloqueada |
| `DELETED` | Deletada |

---

## Regras e restrições

- Resposta máxima: **2000 caracteres**
- Somente o seller do item pode responder
- Perguntas `CLOSED_UNANSWERED` não podem mais ser respondidas
- O sistema pode bloquear compradores específicos de fazer perguntas
- Perguntas podem conter texto traduzido automaticamente (`text_translated`)

---

## Erros comuns

| Código | Causa | Solução |
|--------|-------|---------|
| 401 | Token expirado | Renovar via refresh_token |
| 403 | Seller não é dono do item | Verificar item_id e seller_id |
| 404 | Pergunta não encontrada | Verificar question_id |
| 429 | Rate limit atingido (1500 req/min) | Aguardar e retentar com backoff |

---

## Como as perguntas chegam ao sistema

O sistema usa **dois mecanismos** para não perder perguntas:

1. **Webhook** (`questions`) — notificação em tempo real quando nova pergunta chega
2. **Polling** — busca ativa a cada `POLLING_INTERVAL_SEGUNDOS` (padrão 60s) para pegar perguntas que vieram antes do serviço iniciar

As mensagens pós-venda de compradores que já compraram chegam **apenas por webhook** (`messages`) — não há polling para elas.

---

## Rate limit

- **1500 requisições por minuto** por seller autenticado
- HTTP 429 quando excedido (body vazio)
- Implementar backoff exponencial ao receber 429
