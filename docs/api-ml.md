# API Mercado Livre

## O que funciona

| Endpoint | Método | Função |
|----------|--------|--------|
| `/questions/search` | GET | Lista perguntas UNANSWERED do vendedor |
| `/answers` | POST | Responde uma pergunta |
| `/messages/packs/{pack_id}/sellers/{seller_id}` | POST | Envia mensagem pós-venda |

## Sem permissão (403/404)

| Endpoint | Erro | Workaround |
|----------|------|------------|
| `GET /items/{item_id}` | 403 | Exibe link `produto.mercadolivre.com.br/MLB-ID` |
| `GET /messages/packs/{pack_id}/sellers/{seller_id}` | 404 | Notifica humano para ver no ML |
| `GET /messages/packs` (listar conversas) | 404 | — |
| `GET /orders/search` | 403 | — |
| `GET /users/{id}/items/search` | 403 | — |

## Permissões do App

- App ID: `6430370493736967`
- Escopo configurado: `offline_access read write`
- Permissão no ML Developer: "comunicações pré e pós-venda"
- Permissões que faltam para funcionalidade completa:
  - Leitura de mensagens pós-venda
  - Leitura de itens/pedidos

## Token de Autenticação

- **Access token:** válido por 6 horas
- **Refresh token:** renova automaticamente (se configurado)
- Se `ML_REFRESH_TOKEN` vazio → token expira em 6h → sistema para
- Renovar manualmente: `uv run python auth_ml.py`

## Webhooks Recebidos

O ML envia webhooks para `https://<railway-url>/webhook`:

| Topic | Resource | Ação atual |
|-------|----------|------------|
| `questions` | `/questions/{id}` | Roda ciclo completo |
| `messages` | `{uuid}` | Debounce 8s → notifica Telegram |
| `orders_v2` | `/orders/{id}` | Ignorado |
| `shipments` | `/shipments/{id}` | Ignorado |
| `items` | `/items/{id}` | Ignorado |
