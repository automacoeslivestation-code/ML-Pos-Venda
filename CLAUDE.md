# Pos-Venda ML

Sistema automatico de resposta a perguntas e mensagens de pos-venda no Mercado Livre.
Nicho: cameras de seguranca e acessorios.

## Comandos

```bash
# Rodar em loop continuo
uv run python main.py

# Rodar um unico ciclo (teste / cron externo)
uv run python main.py --ciclo

# Testes
uv run python -m pytest tests/ -v
```

## Stack

- Python 3.12+, uv
- Anthropic SDK (claude-sonnet-4-6)
- httpx (chamadas API ML e Telegram)
- python-dotenv
- python-telegram-bot / httpx para Telegram
- APScheduler (opcional para deploy em Railway)

## Regra de Uso de Agentes Claude

**OBRIGATORIO — duas regras sem excecao:**

- **PLANEJAR / ANALISAR / INVESTIGAR** qualquer coisa neste projeto → disparar `pos-venda-explorer` ANTES de qualquer resposta ou decisao
- **IMPLEMENTAR / CORRIGIR / EXECUTAR** qualquer coisa neste projeto → disparar `pos-venda-dev` para fazer o trabalho

Nunca implementar diretamente no contexto principal. Nunca analisar sem o explorer. O arquiteto coordena — os agentes executam.

| Tarefa | Agente correto |
|--------|----------------|
| Explorar codigo, entender fluxo, investigar bug | `pos-venda-explorer` |
| Planejar nova feature ou mudanca de arquitetura | `pos-venda-explorer` |
| Implementar feature, corrigir bug, escrever teste | `pos-venda-dev` |
| Qualquer duvida sobre o que um modulo faz | `pos-venda-explorer` |

## Agentes do Sistema (codigo)

| Agente | Arquivo | Funcao |
|--------|---------|--------|
| Orquestrador | agents/orquestrador.py | Loop principal, coordena todos |
| Monitor | agents/monitor.py | Busca perguntas e mensagens novas via API ML |
| Analisador | agents/analisador.py | Classifica intencao com Claude |
| Especialista | agents/especialista.py | Carrega base de conhecimento relevante |
| Respondedor | agents/respondedor.py | Gera resposta com Claude e posta via API ML |
| Escalador | agents/escalador.py | Notifica humano via Telegram se confianca baixa |

## Fluxo

```
Monitor → Analisador → Especialista → Respondedor
                                           |
                              confianca >= 0.75 → posta no ML
                              confianca < 0.75  → Escalador → Telegram
```

## Configuracao

Copie `.env.example` para `.env` e preencha:
- `ANTHROPIC_API_KEY`
- `ML_CLIENT_ID`, `ML_CLIENT_SECRET`, `ML_REFRESH_TOKEN`, `ML_SELLER_ID`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Base de Conhecimento

Em `base_conhecimento/`:
- `produtos.md` — specs e informacoes dos produtos
- `faq.md` — perguntas frequentes
- `garantia.md` — politica de garantia e devolucao
- `instalacao.md` — guia de instalacao

**Preencha esses arquivos com os dados reais da sua loja antes de rodar em producao.**

## Autenticacao ML

A API do ML usa OAuth2 com refresh token. O `MLClient` renova o access token automaticamente.
Para obter o refresh token inicial, siga o fluxo de autorizacao OAuth do ML Developer.

## Deploy (Railway)

1. Crie projeto no Railway, conecte este repositorio
2. Configure as variaveis de ambiente (.env)
3. Start command: `uv run python main.py`

---

## Status atual (2026-04-15)

### Concluido
- Estrutura completa do projeto criada
- 6 agentes implementados (orquestrador, monitor, analisador, especialista, respondedor, escalador)
- 11 testes passando (test_analisador, test_respondedor, test_escalador)
- config.py corrigido para nao explodir sem .env
- Script de autenticacao OAuth criado: `auth_ml.py`
- App criado no ML Developer com permissao "comunicacoes pre e pos-venda"
- URI de redirect configurada: `https://webhook.site/88a9cc8f-8539-4cb5-b575-fb785b3cc0fe`
- `.env` criado com ML_CLIENT_ID e ML_CLIENT_SECRET preenchidos

### Proximo passo (retomar aqui amanha)
Rodar o script de autenticacao para gerar o ML_REFRESH_TOKEN:

```bash
cd C:\Users\ADM\projetos\ml-pos-venda
uv run python auth_ml.py
```

O script abre o navegador, voce loga no ML, autoriza o app, e copia o `code` que aparece
no webhook.site para o terminal. O refresh token e salvo automaticamente no .env.

### Ordem restante
1. Gerar ML_REFRESH_TOKEN via auth_ml.py
2. Configurar bot Telegram (BotFather) e preencher TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
3. Preencher ANTHROPIC_API_KEY no .env
4. Testar um ciclo real: `uv run python main.py --ciclo`
5. Deploy no Railway
