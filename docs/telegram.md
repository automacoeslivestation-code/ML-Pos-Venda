# Telegram — Comandos e Fluxo

## Bot

- Nome: `posvendamlbot`
- Token: configurado em `TELEGRAM_BOT_TOKEN`
- Chat ID: `1017474628` (configurado em `TELEGRAM_CHAT_ID`)
- Polling a cada 10s (loop independente do webhook ML)

## Comandos

### `/r` — Responder uma pergunta pendente

```
/r <id> <sua resposta>
```

**Exemplo:**
```
/r 13565064316 Sim, funciona com Wi-Fi 2.4GHz
```

**O que acontece:**
1. Busca o ID em `pendentes.json`
2. Formatador polida: adiciona saudação + horário + tom profissional
3. Posta no ML (pergunta ou mensagem pós-venda)
4. Salva em `memoria.json` para aprendizado futuro
5. Remove de `pendentes.json`
6. Confirma no Telegram

**Erros possíveis:**
- `ID não encontrado ou já respondido` → ID errado ou já processado
- `Formato inválido. Use: /r <id> <sua resposta>` → faltou o ID ou resposta

---

### `/listar` — Ver todas as pendentes

```
/listar
```

**O que retorna** (uma mensagem por pendente):
```
❓ https://produto.mercadolivre.com.br/MLB-4342729373

Comprador: Funciona com Chip ?

/r 13565064316 sua resposta aqui
```

Se não houver pendentes: `Nenhuma pergunta pendente.`

---

## Notificações Automáticas

### Pergunta nova (baixa confiança)
```
❓ https://produto.mercadolivre.com.br/MLB-4342729373

Comprador: Boa tarde funciona wi-fi 5 ghz

/r 13564329137 sua resposta aqui
```

### Mensagem pós-venda
```
💬 Nova mensagem de comprador
Ver no ML: https://www.mercadolivre.com.br/mensagens
```

### Confirmação após `/r`
```
Postado no ML:

Boa tarde, João! Sim, essa câmera funciona com Wi-Fi 2.4GHz.

Base atual: 5 exemplos.
```

---

## Saudação Automática (Formatador)

O sistema adiciona saudação baseada no horário de Brasília:

| Horário | Saudação |
|---------|----------|
| 05:00 – 11:59 | Bom dia |
| 12:00 – 17:59 | Boa tarde |
| 18:00 – 04:59 | Boa noite |

**Regras do Formatador:**
- NUNCA inventa informações
- NUNCA remove o que foi digitado
- Apenas melhora a forma e corrige gramática
- Adiciona `Olá, [Nome]!` + saudação no início
