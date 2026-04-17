# Base de Conhecimento e Configuração

O que precisa ser configurado antes de o sistema funcionar corretamente em produção.

---

## Estrutura de arquivos

```
base_conhecimento/
├── produtos.md      ← specs dos seus produtos
├── faq.md           ← perguntas frequentes
├── garantia.md      ← política de garantia e devolução
├── instalacao.md    ← guia de instalação
├── politicas.md     ← política de troca, cancelamento, NF
├── memoria.json     ← gerado automaticamente pelo sistema
└── pendentes.json   ← gerado automaticamente pelo sistema

templates/
├── compra.md        ← template mensagem de compra confirmada
├── envio.md         ← template mensagem de produto enviado
└── entrega.md       ← template mensagem de produto entregue
```

---

## Qual arquivo é usado quando

O `Especialista` decide quais arquivos carregar baseado na intenção classificada:

| Intenção detectada | Arquivos carregados |
|--------------------|---------------------|
| Qualquer | `produtos.md` + `faq.md` |
| `duvida_tecnica` | + `instalacao.md` |
| `troca_devolucao` | + `garantia.md` + `politicas.md` |
| `reclamacao` | + `garantia.md` + `politicas.md` |
| Qualquer | + últimos 5 exemplos de `memoria.json` (aprendizado) |

> **Atenção:** `memoria.json` e `pendentes.json` são gerados automaticamente. Não edite manualmente.

---

## produtos.md

**Usado em:** Todas as respostas (sempre carregado)

**O que colocar:** Especificações técnicas de cada produto que você vende. Quanto mais completo, melhores as respostas automáticas.

**Formato sugerido:**
```markdown
# Produtos

## Câmeras IP / WiFi

### [Nome exato do produto no ML]
- Resolução: Xmp
- Conexão: WiFi 2.4GHz ou cabo RJ45
- Visão noturna: Até Xm (infravermelho)
- Ângulo de visão: X graus
- Armazenamento: Cartão SD até XGB / Nuvem / NVR
- App: [nome do app], compatível iOS e Android
- Alimentação: 12V/1A (fonte inclusa)
- Proteção: IP66 (para ambientes externos) / IP67
- Temperatura de operação: -20°C a 60°C
- Garantia: 12 meses

### [Próximo produto]
...

## Câmeras Analógicas / HDCVI / AHD

### [Nome do produto]
- Resolução: Xmp / XK
- Tipo: HDCVI / AHD / TVI / CVBS
- Visão noturna: Até Xm
- Compatível com: DVRs HDCVI/AHD/TVI/CVBS
- Cabo: Coaxial (até 500m para HDCVI)
...

## DVRs e NVRs

### [Nome do produto]
- Canais: X canais
- Resolução de gravação: X
- HD incluso: Sim (XTB) / Não
- Acesso remoto: App [nome], PC
...

## Acessórios

### [Nome do produto]
- Compatível com: [lista de produtos]
- Especificações: ...
```

---

## faq.md

**Usado em:** Todas as respostas (sempre carregado)

**O que colocar:** Perguntas que você recebe com mais frequência, com a resposta exata que você daria.

**Formato sugerido:**
```markdown
# Perguntas Frequentes

## Entrega e Prazo

**Quanto tempo demora para chegar?**
Os pedidos são enviados em 1-2 dias úteis após confirmação do pagamento. O prazo de entrega varia por região.

**Vocês enviam para todo o Brasil?**
Sim, enviamos para todo o território nacional via Mercado Envios.

**Posso retirar pessoalmente?**
Não, trabalhamos apenas com envio pelos Correios / transportadoras do Mercado Livre.

## Compatibilidade

**As câmeras WiFi funcionam sem internet?**
As câmeras IP precisam de internet para acesso remoto. Localmente, podem gravar em cartão SD mesmo sem internet.

**Câmera X é compatível com DVR marca Y?**
Câmeras analógicas HDCVI são compatíveis com DVRs que suportem o padrão HDCVI. Câmeras IP funcionam com qualquer NVR via RTSP ou ONVIF.

**Funciona com o app [nome]?**
[Resposta específica por produto]

## Instalação

**Precisa de técnico para instalar?**
As câmeras WiFi são plug-and-play. Basta ligar na tomada, conectar ao WiFi pelo app e está pronto. Câmeras externas analógicas precisam de cabeamento, mas o processo é simples com o manual incluso.

## Pagamento

**Quais formas de pagamento aceitam?**
Aceitamos todas as formas disponíveis no Mercado Livre: cartão de crédito, boleto, Pix e Mercado Pago.

**Têm parcelamento?**
Sim, conforme as opções disponíveis no Mercado Livre para cada produto.
```

---

## garantia.md

**Usado em:** Perguntas sobre troca, devolução e reclamações

**O que colocar:** Sua política real de garantia e como o cliente aciona.

**Formato sugerido:**
```markdown
# Garantia e Devolução

## Prazo de Garantia

- Câmeras e DVRs/NVRs: 12 meses contra defeitos de fabricação
- Acessórios (fontes, suportes, cabos): 3 meses
- A garantia não cobre: danos por mau uso, quedas, infiltração de água além do IP declarado

## Como Acionar a Garantia

1. Entre em contato via mensagens do Mercado Livre
2. Descreva o defeito e envie foto ou vídeo do problema
3. Avaliamos o caso em até 24 horas
4. Se confirmado defeito: enviamos produto novo ou fazemos reparo sem custo

## Devolução (Arrependimento)

- Prazo: 7 dias corridos após recebimento (Código de Defesa do Consumidor)
- Produto deve estar na embalagem original, sem sinais de uso
- Frete de retorno: por nossa conta
- Reembolso: em até 5 dias úteis após recebermos o produto

## Produto com Defeito

- Prazo para reportar: dentro da garantia (12 meses)
- Solução: troca por produto igual ou reembolso total
- Frete: por nossa conta

## Produto Diferente do Anunciado

- Solução imediata: troca ou reembolso total
- Frete: por nossa conta
```

---

## instalacao.md

**Usado em:** Perguntas sobre dúvidas técnicas e instalação

**O que colocar:** Guias de instalação para cada tipo de produto.

**Formato sugerido:**
```markdown
# Guia de Instalação

## Câmeras WiFi (IP)

### Passo a passo básico
1. Baixe o app [nome do app] na App Store ou Google Play
2. Crie uma conta ou faça login
3. Ligue a câmera na tomada (fonte 12V inclusa)
4. No app, toque em "Adicionar dispositivo"
5. Escaneie o QR Code da câmera ou insira o código serial
6. Siga o assistente para conectar à rede WiFi

### Requisitos de rede
- WiFi 2.4GHz (a maioria das câmeras não suporta 5GHz)
- Senha da rede WiFi disponível durante configuração
- Roteador com acesso à internet para acesso remoto

### Problemas comuns
**Câmera não aparece no app:**
- Confirme que está na rede 2.4GHz
- Reinicie o roteador e a câmera
- Mantenha câmera e celular na mesma rede durante configuração

**Imagem com lag ou travando:**
- Problema de velocidade de internet
- Reduza a resolução de transmissão no app

## Câmeras Analógicas (HDCVI/AHD)

### Materiais necessários
- Cabo coaxial (não incluso) — recomendado RG59 ou RG6
- Fonte de alimentação 12V (inclusa)
- DVR compatível com HDCVI/AHD

### Instalação
1. Passe o cabo coaxial do DVR até o ponto da câmera
2. Conecte o cabo BNC na câmera e no canal do DVR
3. Conecte a alimentação 12V
4. O DVR detectará a câmera automaticamente

### Distância máxima de cabo
- HDCVI: até 500m com cabo RG59
- AHD: até 200m com cabo RG59

## DVRs e NVRs

### Acesso remoto
1. Conecte o DVR ao roteador via cabo de rede (RJ45)
2. No menu do DVR, acesse Configurações > Rede
3. Anote o número de série do aparelho
4. Baixe o app [nome] e adicione o dispositivo pelo número de série
```

---

## politicas.md

**Usado em:** Perguntas sobre troca, devolução e reclamações (junto com `garantia.md`)

**O que colocar:** Regras da loja sobre cancelamento, NF, prazos de resposta.

O arquivo foi criado com um modelo base. Edite conforme sua política real.

---

## Templates de follow-up

### templates/compra.md

Instruções para Claude gerar a mensagem de "pedido confirmado".

**Dados disponíveis para personalizar:**
- `nome_comprador` — nickname do comprador no ML
- `produto` — nome do primeiro item do pedido
- `order_id` — número do pedido

**Regras importantes:**
- Máximo 350 caracteres na mensagem final
- Tom: caloroso e profissional
- Não mencionar prazo específico se não tiver certeza
- Não pedir avaliação (contra políticas do ML)

### templates/envio.md

Instruções para a mensagem de "produto enviado".

**Regras:**
- Informar que pode rastrear pelo próprio ML
- Não prometer data de entrega específica
- Máximo 350 caracteres

### templates/entrega.md

Instruções para a mensagem de "produto entregue".

**Regras:**
- NÃO pedir avaliação (violação das políticas do ML — pode resultar em penalidade)
- Oferecer suporte pós-venda
- Máximo 350 caracteres

---

## memoria.json (gerado automaticamente)

Toda vez que o humano responde uma pendente com `/r <id> <texto>`, o sistema salva o par pergunta → resposta no `memoria.json`. Isso cria uma base de exemplos aprovados que o Claude usa como contexto nas próximas respostas.

**Não é necessário criar ou editar manualmente.**

Estrutura gerada:
```json
[
  {
    "pergunta": "Essa câmera funciona com DVR marca Intelbras?",
    "resposta": "Boa tarde! Sim, nossa câmera HDCVI é compatível com DVRs Intelbras que suportam o padrão HDCVI. Qualquer dúvida é só chamar!",
    "intencao": "duvida_tecnica",
    "data": "2026-04-17"
  }
]
```

Com o tempo, esse arquivo cresce e as respostas automáticas ficam cada vez mais precisas para o seu nicho.

---

## Checklist antes de ir para produção

**Base de conhecimento (obrigatório):**
- [ ] `produtos.md` preenchido com specs reais de todos os produtos
- [ ] `faq.md` preenchido com as perguntas mais comuns que você recebe
- [ ] `garantia.md` preenchido com sua política real
- [ ] `instalacao.md` preenchido com guias dos produtos que vende
- [ ] `politicas.md` revisado com suas regras de cancelamento e NF

**Templates (obrigatório):**
- [ ] `templates/compra.md` revisado com o tom da sua loja
- [ ] `templates/envio.md` revisado
- [ ] `templates/entrega.md` revisado (sem pedido de avaliação)

**Variáveis de ambiente (obrigatório):**
- [ ] `ANTHROPIC_API_KEY` configurada
- [ ] `ML_CLIENT_ID` e `ML_CLIENT_SECRET` configurados
- [ ] `ML_REFRESH_TOKEN` obtido via `/callback`
- [ ] `ML_SELLER_ID` configurado
- [ ] `ML_REDIRECT_URI` configurado (URL pública do /callback)
- [ ] `TELEGRAM_BOT_TOKEN` configurado
- [ ] `TELEGRAM_CHAT_ID` configurado (seu chat_id pessoal)

**ML Developer (obrigatório):**
- [ ] Permissão "Comunicação pré e pós-venda" ativada (leitura e escrita)
- [ ] URL de notificação configurada: `https://seu-app.railway.app/webhook`
- [ ] Topics ativos: `questions`, `messages`, `orders_v2`, `shipments`

**Ajuste de confiança (recomendado):**
- Começar com `CONFIANCA_MINIMA=0.75` (padrão)
- Se muitas respostas ruins passando automaticamente → aumentar para 0.85
- Se muitas respostas boas sendo escaladas → diminuir para 0.70
