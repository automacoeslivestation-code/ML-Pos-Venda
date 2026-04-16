# Deploy e Configuração

## Variáveis de Ambiente

### Obrigatórias
```
ANTHROPIC_API_KEY              # chave da Anthropic
ML_CLIENT_ID                   # ID do app no ML Developer
ML_CLIENT_SECRET               # secret do app
ML_SELLER_ID                   # ID do vendedor (gerado por auth_ml.py)
TELEGRAM_BOT_TOKEN             # token do bot (@BotFather)
TELEGRAM_CHAT_ID               # seu chat ID (use @myidbot)
```

### Token ML — escolher um
```
ML_REFRESH_TOKEN               # recomendado: renova automaticamente
ML_ACCESS_TOKEN                # fallback: expira em 6h
```

### Opcionais
```
CONFIANCA_MINIMA=0.75          # threshold para postar sem humano
POLLING_INTERVAL_SEGUNDOS=60   # intervalo em modo polling
```

## Como Rodar

```bash
# Webhook — padrão Railway
uv run python main.py

# Polling contínuo — fallback sem webhook
uv run python main.py --polling

# Ciclo único — teste pontual
uv run python main.py --ciclo

# Testes
uv run python -m pytest tests/ -v

# Gerar/renovar token ML
uv run python auth_ml.py
```

## Railway

1. Fazer push para `github.com/Browsher/ML-Pos-Venda`
2. Conta com fork sincroniza → Railway deploya automaticamente
3. Configurar variáveis em Settings → Variables
4. URL do servidor: `https://ml-pos-venda-production-3f78.up.railway.app`
5. Webhook ML Developer: `https://ml-pos-venda-production-3f78.up.railway.app/webhook`

## ML Developer

- App: `https://developers.mercadolivre.com.br/`
- Webhook URL configurada no app para receber notificações
- Tópicos habilitados: questions, messages, orders_v2, shipments

## Ciclo de Deploy

```
Editar código local
    ↓
git push origin master
    ↓
Sincronizar fork no GitHub (Sync fork)
    ↓
Railway detecta → deploya automaticamente (~1-2 min)
    ↓
Checar logs no Railway
```
