# Arquitetura: ML Pós-Venda

## Fluxo Principal

```
Webhook ML (topic=questions)
        ↓
    Orquestrador.ciclo()
        ↓
    Monitor.buscar_novas()        → lista de Interacao
        ↓
    Analisador.analisar()         → Analise (intencao, resumo, urgente)
        ↓
    Especialista.contexto_para()  → base de conhecimento relevante
        ↓
    Respondedor.gerar_e_postar()  → Resposta (texto, confianca, postada)
        ↓
    confianca >= 0.75 → posta no ML automaticamente
    confianca <  0.75 → Escalador.escalar() → Telegram
```

## Fluxo de Resposta Humana

```
Humano envia /r <id> <texto> no Telegram
        ↓
    TelegramListener._processar_resposta()
        ↓
    Formatador.formatar()         → saudacao + hora + polimento
        ↓
    MLClient.responder_pergunta() ou responder_mensagem()
        ↓
    Memoria.adicionar()           → salva para aprendizado
        ↓
    Pendentes.remover()
        ↓
    Confirmacao no Telegram
```

## Fluxo de Mensagens Pós-Venda

```
Webhook ML (topic=messages, resource=UUID)
        ↓
    debounce 8s por pack_id
    (aguarda mensagens subsequentes do mesmo comprador)
        ↓
    Orquestrador.processar_mensagem_pack()
        ↓
    Escalador.escalar_mensagem_simples()
        ↓
    Telegram: "💬 Nova mensagem. Ver no ML"
```

---

## Agentes

| Agente | Arquivo | Entrada | Saída |
|--------|---------|---------|-------|
| Orquestrador | orquestrador.py | Webhook / loop | Coordena todos |
| Monitor | monitor.py | API ML | Lista de Interacao |
| Analisador | analisador.py | Interacao | Analise |
| Especialista | especialista.py | intencao (str) | contexto (str) |
| Respondedor | respondedor.py | Interacao + Analise + contexto | Resposta |
| Escalador | escalador.py | Interacao + Analise + Resposta | Telegram |
| TelegramListener | telegram_listener.py | Updates Telegram | Resposta no ML |
| Formatador | formatador.py | texto bruto + nome | texto polido |
| Pendentes | pendentes.py | dados da escalada | pendentes.json |
| Memoria | memoria.py | pergunta + resposta | memoria.json |

---

## Decisões Técnicas

| Decisão | Motivo |
|---------|--------|
| Pendentes sempre relê do disco | Evita race condition entre Escalador e TelegramListener |
| Debounce 8s para mensagens | Acumula mensagens seguidas do mesmo comprador |
| Especialista com cache em memória | Evita reler arquivos .md a cada ciclo |
| Retry automático em 401 | Renova token e repete a requisição sem interrupção |
| Fallback intencao=OUTRO | Se Claude falhar no JSON, escala para humano em vez de crashar |
| Loop Telegram independente (10s) | /r funciona sem depender de webhook do ML |
| Startup cycle (2s delay) | Pega perguntas abertas que chegaram durante downtime |
| chat_id convertido para int | Evita rejeição do Telegram por tipo incorreto |
| Mensagem truncada em 4096 chars | Limite do Telegram |

---

## Estrutura de Arquivos

```
ml-pos-venda/
├── agents/
│   ├── orquestrador.py
│   ├── monitor.py
│   ├── analisador.py
│   ├── especialista.py
│   ├── respondedor.py
│   ├── escalador.py
│   ├── telegram_listener.py
│   ├── formatador.py
│   ├── pendentes.py
│   └── memoria.py
├── base_conhecimento/
│   ├── produtos.md       ← preencher com specs reais
│   ├── faq.md            ← preencher com perguntas comuns
│   ├── garantia.md       ← preencher com políticas
│   ├── instalacao.md     ← preencher com guias
│   ├── memoria.json      ← auto-gerado (respostas aprovadas)
│   └── pendentes.json    ← auto-gerado (aguardando resposta)
├── docs/
│   ├── arquitetura.md    ← este arquivo
│   ├── api-ml.md         ← endpoints e limitações da API ML
│   ├── deploy.md         ← variáveis de ambiente e Railway
│   └── telegram.md       ← comandos e notificações
├── tests/
├── ml_client.py
├── webhook_server.py
├── config.py
├── auth_ml.py
└── main.py
```

---

## Intenções Suportadas (Analisador)

| Valor | Quando usar |
|-------|-------------|
| `duvida_tecnica` | Perguntas sobre especificações, compatibilidade |
| `prazo_entrega` | "Quando chega?", "Qual o prazo?" |
| `troca_devolucao` | "Quero devolver", "Veio errado" |
| `reclamacao` | "Não funciona", "Com defeito" |
| `confirmacao_pedido` | "Confirma meu pedido?" |
| `outro` | Não classificado → sempre escala para humano |
