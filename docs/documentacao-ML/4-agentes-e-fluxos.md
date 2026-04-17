# Agentes e Fluxos Internos do Sistema

Documentação completa de cada agente, seus comportamentos, dependências e edge cases.

---

## Arquitetura geral

```
Webhook ML / Polling
        ↓
   Orquestrador
        ↓
   Monitor → Analisador → Especialista → Respondedor
                                              ↓
                             confiança >= 0.75 → posta no ML automaticamente
                             confiança < 0.75  → Escalador → Telegram
                                                                  ↓
                                                      Humano digita /r <id> <texto>
                                                                  ↓
                                                         TelegramListener
                                                                  ↓
                                                           Formatador → posta no ML
                                                                  ↓
                                                            Memoria (salva exemplo)
```

---

## Agente: Orquestrador

**Arquivo:** `agents/orquestrador.py`

**Função:** Coordena todos os outros agentes. Ponto de entrada para processar interações.

**Métodos:**

| Método | Chamado por | O que faz |
|--------|-------------|-----------|
| `ciclo()` | webhook `/webhook` (questions) e startup | Processa respostas pendentes do Telegram + busca novas perguntas |
| `processar_mensagem_pack(resource_id)` | webhook `/webhook` (messages) | Resolve UUID → pack_id, lê mensagem do comprador, escala para humano |
| `_buscar_status_pedido(order_id)` | `processar_mensagem_pack` | Busca status legível: "Não enviado" / "Em trânsito" / "Entregue" / "Cancelado" |
| `rodar()` | `main.py --polling` | Loop infinito de polling com intervalo `POLLING_INTERVAL_SEGUNDOS` |

**Resolução de UUID → pack_id:**
```python
# Webhook de messages manda UUID (contém "-"), não pack_id
if "-" in resource_id:
    msg = ml.buscar_mensagem_por_uuid(resource_id)
    pack_id = str(msg.get("pack_id") or resource_id)
```

---

## Agente: Monitor

**Arquivo:** `agents/monitor.py`

**Função:** Busca perguntas novas na API do ML e converte em objetos `Interacao`.

**O que busca:** Apenas **perguntas** (`/questions/search?status=UNANSWERED`). Mensagens pós-venda chegam por webhook, não por polling.

**Deduplicação:** Set `_respondidas` em memória — se reiniciar, perguntas recentes podem ser processadas de novo (benigno, pois a API já marcou como respondida).

**Estrutura `Interacao`:**

| Campo | Tipo | Origem |
|-------|------|--------|
| `tipo` | TipoInteracao | PERGUNTA ou MENSAGEM |
| `id` | str | question_id ou pack_id |
| `texto` | str | Texto da pergunta/mensagem |
| `item_id` | str | ID do anúncio (MLB...) |
| `nome_comprador` | str | `from.id` numérico (não é nome legível) |
| `historico` | list[str] | Últimas mensagens da conversa |

> **Importante:** `nome_comprador` armazena o ID numérico do comprador (`from.id`), não o nome real. Para obter o nome seria necessário `api_version=4`, mas isso não está implementado.

---

## Agente: Analisador

**Arquivo:** `agents/analisador.py`

**Função:** Classifica a intenção da mensagem do comprador usando Claude.

**Intenções suportadas:**

| Intenção | Exemplos de pergunta |
|----------|---------------------|
| `duvida_tecnica` | "Como instalo?", "É compatível com...?", "Qual o alcance?" |
| `prazo_entrega` | "Quando chega?", "Qual o prazo de envio?" |
| `troca_devolucao` | "Quero devolver", "Veio diferente do anúncio" |
| `reclamacao` | "Produto com defeito", "Não funciona" |
| `confirmacao_pedido` | "Meu pedido foi confirmado?" |
| `outro` | Qualquer coisa fora das categorias acima |

**Formato de resposta esperado do Claude:**
```json
{"intencao": "duvida_tecnica", "resumo": "pergunta sobre compatibilidade", "urgente": false}
```

**Fallback:** Se o JSON não puder ser parseado → retorna `intencao=outro, urgente=False`. Nunca trava.

**Limites:**
- Histórico: últimas 5 mensagens
- Max tokens: 200

---

## Agente: Especialista

**Arquivo:** `agents/especialista.py`

**Função:** Monta o contexto da base de conhecimento baseado na intenção classificada.

**O que carrega por intenção:**

| Intenção | Arquivos carregados |
|----------|---------------------|
| Qualquer | `produtos.md` + `faq.md` |
| `duvida_tecnica` | + `instalacao.md` |
| `troca_devolucao` | + `garantia.md` + `politicas.md` |
| `reclamacao` | + `garantia.md` + `politicas.md` |
| Qualquer | + exemplos aprovados de `memoria.json` (últimos 5 por intenção) |

**Cache:** Arquivos são lidos do disco uma vez e cacheados em memória. Se o conteúdo do `.md` mudar em runtime, o cache não é invalidado (requer restart).

**Arquivo faltando:** Se algum `.md` não existir, retorna string vazia silenciosamente — nunca lança erro.

---

## Agente: Respondedor

**Arquivo:** `agents/respondedor.py`

**Função:** Gera a resposta usando Claude + decide se posta automaticamente.

**Fluxo:**
1. Recebe `Interacao` + `Analise` + `contexto` (base de conhecimento)
2. Monta prompt com contexto + intenção + histórico + pergunta
3. Chama Claude (max 600 tokens)
4. Extrai a linha `CONFIANCA: X.X` da resposta
5. Se confiança >= `CONFIANCA_MINIMA` (padrão 0.75) → posta no ML
6. Se confiança < 0.75 → retorna sem postar (Orquestrador vai escalar)

**Parsing de confiança:**
```
CONFIANCA: 0.92   ← funciona
CONFIANÇA: 0.92   ← NÃO funciona (acento na letra A quebra o parsing)
```

**Fallback de confiança:** Se não encontrar a linha ou não conseguir parsear o float → usa `CONFIANCA_MINIMA - 0.1` (ex: 0.65), que fica abaixo do limite → escala para o humano.

**Limites de caracteres aplicados em `ml_client.py`:**
- Perguntas: 2000 chars máximo
- Mensagens pós-venda: 350 chars máximo

---

## Agente: Formatador

**Arquivo:** `agents/formatador.py`

**Função:** Polida a resposta do humano antes de postar no ML.

**O que faz:**
1. Determina saudação por horário local:
   - 05h–11h59 → "Bom dia"
   - 12h–17h59 → "Boa tarde"
   - 18h–04h59 → "Boa noite"
2. Monta: `"{Saudação}, {nome}! "` + chama Claude para reformular o corpo
3. Claude apenas melhora gramática/tom — nunca inventa informação nova

**Chamado por:** `TelegramListener` quando humano usa `/r <id> <resposta>`

---

## Agente: Escalador

**Arquivo:** `agents/escalador.py`

**Função:** Notifica o humano no Telegram e salva a interação em pendentes.

**Três cenários:**

| Método | Quando | Mensagem enviada |
|--------|--------|-----------------|
| `escalar()` | Confiança baixa em pergunta | `❓ link-do-produto\n\nComprador: <texto>\n\n/r <id>` |
| `escalar_mensagem()` | Mensagem pós-venda recebida | `💬 Pós-venda \| Em trânsito\n\nComprador: <texto>\n\n/r <pack_id>` |
| `escalar_mensagem_simples()` | Erro ao buscar conteúdo da mensagem | `💬 Nova mensagem de comprador\nVer no ML: <link>` |

**Formato do link de produto:** `MLB4342729373` → `MLB-4342729373` → `https://produto.mercadolivre.com.br/MLB-4342729373`

**Limite do Telegram:** 4096 chars por mensagem (trunca com "..." se necessário)

**Persistência:** Salva em `base_conhecimento/pendentes.json` com todos os campos necessários para o TelegramListener processar depois.

---

## Agente: TelegramListener

**Arquivo:** `agents/telegram_listener.py`

**Função:** Recebe e processa comandos do humano no Telegram.

**Segurança:** Só processa mensagens do `TELEGRAM_CHAT_ID` configurado. Outros chat_ids são ignorados.

**Polling:** Chamado a cada 10 segundos pelo loop em `webhook_server.py`.

**Comandos:**

| Comando | Comportamento |
|---------|---------------|
| `/r <id> <texto>` | Busca pendente por id → Formatador → posta no ML → salva em Memoria → remove de Pendentes → confirma no Telegram |
| `/listar` | Para cada pendente: mostra tipo (❓ pergunta ou 💬 pós-venda), link do produto ou status do pedido, texto do comprador, comando `/r` pronto |
| `/status` | Total de pendentes por tipo + tamanho da Memoria |
| `/cancelar <id>` | Remove pendente sem responder |
| `/comandos` | Lista todos os comandos |

**Offset:** Mantém `_ultimo_update_id` em memória para não reprocessar updates já vistos.

**Fluxo de `/r`:**
```
Humano: /r q123 Sim, é compatível com qualquer DVR HDCVI
        ↓
Busca pendente q123 em pendentes.json
        ↓
Formatador.formatar("Sim, é compatível...", nome="user123")
        ↓
Claude polida: "Boa tarde! Sim, é compatível com qualquer DVR HDCVI."
        ↓
Se tipo == "pergunta": ml.responder_pergunta(q123, texto)
Se tipo == "mensagem": ml.responder_mensagem(pack_id, texto)
        ↓
Memoria.adicionar(pergunta_original, resposta_final, intencao)
        ↓
Pendentes.remover(q123)
        ↓
Telegram: "Postado no ML:\n\n_Boa tarde! Sim..._\n\nBase atual: 5 exemplos."
```

---

## Agente: Memoria

**Arquivo:** `agents/memoria.py`
**Arquivo em disco:** `base_conhecimento/memoria.json`

**Função:** Persiste respostas aprovadas pelo humano para uso futuro como contexto.

**Estrutura do JSON:**
```json
[
  {
    "pergunta": "Qual a diferença entre câmera IP e analógica?",
    "resposta": "Câmera IP usa rede Ethernet e tem resolução maior...",
    "intencao": "duvida_tecnica",
    "data": "2026-04-17"
  }
]
```

**Como é usada:** O Especialista chama `memoria.formatar_contexto(intencao)` que retorna os últimos 5 exemplos da intenção como string formatada para compor o prompt do Claude.

**Sem deduplicação:** Mesma resposta pode ser salva múltiplas vezes. Sem impacto funcional, apenas tamanho crescente.

---

## Agente: Pendentes

**Arquivo:** `agents/pendentes.py`
**Arquivo em disco:** `base_conhecimento/pendentes.json`

**Função:** Rastreia interações aguardando resposta do humano.

**Estrutura do JSON:**
```json
{
  "q123": {
    "texto": "Essa câmera funciona em -5°C?",
    "intencao": "duvida_tecnica",
    "tipo": "pergunta",
    "nome_comprador": "441782523",
    "titulo_item": "Câmera IP WiFi 2MP",
    "item_id": "MLB4342729373",
    "order_status": "",
    "sugestao": "Sim, a câmera opera entre -20°C e 60°C...",
    "confianca": 0.65
  },
  "2000012546698451": {
    "texto": "Meu produto chegou com defeito",
    "intencao": "mensagem_pos_venda",
    "tipo": "mensagem",
    "nome_comprador": "441782523",
    "titulo_item": "",
    "item_id": "",
    "order_status": "Em trânsito",
    "sugestao": "",
    "confianca": 0.0
  }
}
```

**Chave:** `question_id` para perguntas, `pack_id` para mensagens pós-venda.

---

## Agentes de Follow-up

### Enviador (`agents/enviador.py`)

**Chamado por:** `webhook_server.py` nos handlers de `orders_v2` e `shipments`

**Deduplicação:** Verifica `Enviados.ja_enviou(order_id, evento)` antes de cada envio.

**Extração de dados do pedido:**
- `buyer.nickname` → nome do comprador
- `order_items[0].item.title` → produto
- `pedido.get("pack_id") or order_id` → pack_id para mensagem

### Gerador (`agents/gerador.py`)

**Usa:** Templates em `templates/compra.md`, `templates/envio.md`, `templates/entrega.md`

**Fallback:** Se template não existir → prompt genérico `"Gere uma mensagem de follow-up para o evento: {evento}"`

**Limite:** max_tokens=300 (mensagem curta e direta)

### Enviados (`agents/enviados.py`)

**Arquivo em disco:** `data/enviados.json`

**Estrutura:**
```json
{
  "2000016017263462_compra": true,
  "2000016017263462_envio": true
}
```

**Chave:** `{order_id}_{evento}` — evento é "compra", "envio" ou "entrega"

**Importante:** Arquivo é deletado/zerado a cada redeploy no Railway. Se houver redeploy logo após uma venda, pode enviar mensagem duplicada.

---

## Debounce de mensagens (webhook_server.py)

Evita processar a mesma conversa múltiplas vezes quando o comprador manda várias mensagens seguidas:

```
Comprador manda msg 1 → task agendada para T+8s
Comprador manda msg 2 (T+3s) → task anterior cancelada, nova agendada T+11s
Comprador manda msg 3 (T+6s) → idem, nova agendada T+14s
T+14s → processa apenas a última (mensagem 3)
```

O `resource_id` do debounce é o UUID da mensagem (não pack_id). Mensagens diferentes do mesmo pack têm UUIDs diferentes, então o debounce funciona por UUID.

---

## Inicialização do servidor (webhook_server.py lifespan)

```
startup:
  1. Orquestrador() criado — instancia todos os agentes pós-venda
  2. Enviador() criado — instancia agentes de follow-up
  3. _ciclo_startup() agendado (delay 2s) — busca perguntas em aberto
  4. _loop_telegram() agendado (delay 5s, repeat 10s) — polling do Telegram
  5. FastAPI serve requests

shutdown:
  (sem cleanup especial)
```

---

## Modos de execução (`main.py`)

| Comando | Modo | Quando usar |
|---------|------|-------------|
| `uv run python main.py` | Webhook server (padrão) | Produção no Railway |
| `uv run python main.py --ciclo` | Uma iteração | Debug, teste pontual |
| `uv run python main.py --polling` | Loop de polling | Fallback sem webhook |

---

## O que acontece em cada tipo de falha

| Falha | Comportamento |
|-------|---------------|
| Claude API fora | Exceção propagada — interação não processada, log de erro |
| ML API 401 | Renovação automática com refresh_token + retry |
| ML API 401 sem refresh_token | `TokenExpiradoError` — sistema para |
| ML API 403 | Log de erro, interação não processada |
| ML API 404 | Log de erro, interação não processada |
| Telegram API fora | Log de erro, mensagem não entregue (sem retry) |
| Railway API fora | Log de erro, token salvo em memória mas não persistido |
| JSON corrompido (pendentes/memoria/enviados) | Retorna estrutura vazia, sem erro |
| Template .md não existe | Usa fallback genérico |
| `politicas.md` não existe | String vazia no contexto (sem erro) |
| Perguntas reprocessadas após restart | Benigno — ML rejeita resposta duplicada |
