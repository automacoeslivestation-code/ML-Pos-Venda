# ML Pós-Venda Bot

Sistema automatizado de resposta a perguntas e mensagens de pós-venda no **Mercado Livre**, com aprendizado contínuo via Telegram.

---

## Como funciona

```
Comprador faz pergunta no ML
        ↓
Sistema classifica a intenção
        ↓
Claude gera uma sugestão de resposta
        ↓
Você recebe no Telegram e decide
        ↓
Você responde com /r <id> <texto>
        ↓
Formatador polida: saudação + horário + texto profissional
        ↓
Resposta postada no ML + salva na memória
        ↓
Com o tempo, o sistema aprende e ganha autonomia
```

---

## Agentes

| Agente | Função |
|--------|--------|
| **Monitor** | Busca perguntas e mensagens novas via API ML |
| **Analisador** | Classifica a intenção do comprador |
| **Especialista** | Carrega contexto da base de conhecimento |
| **Respondedor** | Gera sugestão de resposta com IA |
| **Escalador** | Envia para você via Telegram |
| **Formatador** | Polida a resposta antes de postar no ML |
| **Orquestrador** | Coordena tudo em loop contínuo |

---

## Fluxo de aprendizado

Toda resposta aprovada por você é salva em `base_conhecimento/memoria.json`.
Com o tempo, o Claude usa esses exemplos para responder com mais confiança.
Quando a confiança atingir o limiar configurado, ele responde sozinho.

```
Início: CONFIANCA_MINIMA=1.0 → tudo vai pro Telegram
Com experiência: CONFIANCA_MINIMA=0.75 → responde 75%+ sozinho
```

---

## Respondendo via Telegram

Quando chegar uma pergunta, você receberá:

```
❓ Pergunta aguardando sua resposta

Comprador: "A câmera funciona sem fio?"

Sugestão do Claude (60% confiança):
Sim, a câmera possui conectividade WiFi...

Para responder, envie:
/r q123 sua resposta aqui
```

Responda com:
```
/r q123 sim funciona via wifi configura pelo app
```

O Formatador transforma automaticamente em:
```
Boa tarde, João! Sim, a câmera funciona via WiFi. Configure pelo aplicativo.
```

Regras do Formatador:
- Adiciona saudação com nome do comprador e horário do dia
- Reformula para linguagem profissional e cordial
- **Nunca inventa informações** — usa apenas o que você escreveu
- **Nunca remove** o que você escreveu

---

## Base de conhecimento

Em `base_conhecimento/` ficam os arquivos que o Claude usa como referência:

| Arquivo | Conteúdo |
|---------|----------|
| `produtos.md` | Especificações dos produtos |
| `faq.md` | Perguntas frequentes |
| `garantia.md` | Política de garantia e devolução |
| `instalacao.md` | Guia de instalação |
| `memoria.json` | Respostas aprovadas (gerado automaticamente) |

---

## Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/Browsher/ML-Pos-Venda.git
cd ML-Pos-Venda
```

### 2. Configure as variáveis de ambiente
```bash
cp .env.example .env
```

Preencha o `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
ML_CLIENT_ID=
ML_CLIENT_SECRET=
ML_ACCESS_TOKEN=     # gerado pelo auth_ml.py
ML_SELLER_ID=        # gerado pelo auth_ml.py
TELEGRAM_BOT_TOKEN=  # gerado pelo @BotFather
TELEGRAM_CHAT_ID=    # gerado pelo @myidbot
CONFIANCA_MINIMA=1.0
POLLING_INTERVAL_SEGUNDOS=60
```

### 3. Autenticação Mercado Livre
```bash
uv run python auth_ml.py
```

### 4. Instale as dependências
```bash
uv sync
```

### 5. Rode os testes
```bash
uv run python -m pytest tests/ -v
```

### 6. Inicie o servidor
```bash
uv run python main.py
```

---

## Deploy (Railway)

1. Faça fork deste repositório
2. Crie um projeto no [Railway](https://railway.app) conectando o fork
3. Configure as variáveis de ambiente no painel do Railway
4. Configure o **Start Command**: `uv run python main.py`
5. Copie a URL pública gerada pelo Railway
6. No ML Developer, configure a **URL de notificação**: `https://sua-url.railway.app/webhook`

---

## Stack

- Python 3.12+
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) — claude-haiku-4-5
- [FastAPI](https://fastapi.tiangolo.com/) — servidor webhook
- [httpx](https://www.python-httpx.org/) — chamadas API ML e Telegram
- [uv](https://github.com/astral-sh/uv) — gerenciador de pacotes
