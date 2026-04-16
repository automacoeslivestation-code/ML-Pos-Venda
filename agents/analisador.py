"""Analisador: classifica a intencao da mensagem recebida."""
from dataclasses import dataclass
from enum import Enum

import anthropic

from config import config
from agents.monitor import Interacao


class Intencao(Enum):
    DUVIDA_TECNICA = "duvida_tecnica"        # Como instalar, compatibilidade, specs
    PRAZO_ENTREGA = "prazo_entrega"           # Quando chega, rastreio
    TROCA_DEVOLUCAO = "troca_devolucao"       # Produto com defeito, arrependimento
    RECLAMACAO = "reclamacao"                 # Insatisfacao geral
    CONFIRMACAO_PEDIDO = "confirmacao_pedido" # Confirmacao de compra, nota fiscal
    OUTRO = "outro"                           # Fora do escopo


@dataclass
class Analise:
    intencao: Intencao
    resumo: str        # Uma linha descrevendo o que o comprador quer
    urgente: bool      # True se reclamacao ou devolucao


_PROMPT_SISTEMA = """Voce classifica mensagens de compradores no Mercado Livre.
Responda SOMENTE com JSON no formato:
{"intencao": "<valor>", "resumo": "<uma frase>", "urgente": <true|false>}

Valores validos para intencao:
- duvida_tecnica
- prazo_entrega
- troca_devolucao
- reclamacao
- confirmacao_pedido
- outro
"""


class Analisador:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def analisar(self, interacao: Interacao) -> Analise:
        contexto = interacao.texto
        if interacao.historico:
            historico_fmt = "\n".join(f"- {m}" for m in interacao.historico[-5:])
            contexto = f"Historico:\n{historico_fmt}\n\nUltima mensagem: {interacao.texto}"

        msg = self._client.messages.create(
            model=config.MODEL_RESPONDEDOR,
            max_tokens=200,
            system=_PROMPT_SISTEMA,
            messages=[{"role": "user", "content": contexto}],
        )

        import json
        dados = json.loads(msg.content[0].text)
        return Analise(
            intencao=Intencao(dados["intencao"]),
            resumo=dados["resumo"],
            urgente=dados["urgente"],
        )
