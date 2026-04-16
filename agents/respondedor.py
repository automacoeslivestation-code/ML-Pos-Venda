"""Respondedor: gera resposta com Claude e posta via API do ML."""
from dataclasses import dataclass

import anthropic

from config import config
from agents.monitor import Interacao
from agents.analisador import Analise


@dataclass
class Resposta:
    texto: str
    confianca: float   # 0.0 a 1.0
    postada: bool = False


_PROMPT_SISTEMA = """Voce e um atendente de pos-venda especialista em cameras de seguranca e acessorios.
Responda de forma clara, simpatica e objetiva em portugues brasileiro.
Nao mencione precos nem faca promessas que nao estejam na base de conhecimento.

Apos a resposta, adicione uma linha separada com:
CONFIANCA: <numero entre 0.0 e 1.0>

0.0 = completamente incerto | 1.0 = completamente certo

Se nao souber responder com seguranca, coloque confianca abaixo de 0.75 e diga que vai verificar.
"""


class Respondedor:
    def __init__(self, ml_client):
        self._claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._ml = ml_client

    def gerar_e_postar(
        self, interacao: Interacao, analise: Analise, contexto: str
    ) -> Resposta:
        resposta = self._gerar(interacao, analise, contexto)

        if resposta.confianca >= config.CONFIANCA_MINIMA:
            self._postar(interacao, resposta.texto)
            resposta.postada = True

        return resposta

    def _gerar(self, interacao: Interacao, analise: Analise, contexto: str) -> Resposta:
        historico_fmt = ""
        if interacao.historico:
            historico_fmt = "\n".join(f"Comprador: {m}" for m in interacao.historico[-5:])
            historico_fmt = f"\n\nHistorico da conversa:\n{historico_fmt}"

        prompt = f"""Base de conhecimento:
{contexto}

Intencao identificada: {analise.intencao.value}
Resumo: {analise.resumo}
{historico_fmt}

Mensagem do comprador:
{interacao.texto}"""

        msg = self._claude.messages.create(
            model=config.MODEL_RESPONDEDOR,
            max_tokens=600,
            system=_PROMPT_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parsear(msg.content[0].text)

    def _parsear(self, texto_bruto: str) -> Resposta:
        linhas = texto_bruto.strip().split("\n")
        confianca = config.CONFIANCA_MINIMA - 0.1  # default: escalar

        texto_linhas = []
        for linha in linhas:
            if linha.startswith("CONFIANCA:"):
                try:
                    confianca = float(linha.split(":")[1].strip())
                except ValueError:
                    pass
            else:
                texto_linhas.append(linha)

        return Resposta(
            texto="\n".join(texto_linhas).strip(),
            confianca=confianca,
        )

    def _postar(self, interacao: Interacao, texto: str) -> None:
        from agents.monitor import TipoInteracao
        if interacao.tipo == TipoInteracao.PERGUNTA:
            self._ml.responder_pergunta(interacao.id, texto)
        else:
            self._ml.responder_mensagem(interacao.id, texto)
