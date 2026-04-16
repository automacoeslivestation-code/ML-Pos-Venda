"""Escalador: notifica humano via Telegram quando o sistema nao sabe responder."""
import httpx

from config import config
from agents.monitor import Interacao
from agents.analisador import Analise
from agents.respondedor import Resposta
from agents.pendentes import Pendentes


class Escalador:
    def __init__(self):
        self._url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        self._pendentes = Pendentes()

    def escalar(self, interacao: Interacao, analise: Analise, resposta: Resposta) -> None:
        self._pendentes.adicionar(
            interacao_id=interacao.id,
            texto=interacao.texto,
            intencao=analise.intencao.value,
            tipo=interacao.tipo.value,
        )

        emoji = "🚨" if analise.urgente else "❓"
        tipo = "Pergunta" if interacao.tipo.value == "pergunta" else "Mensagem pos-venda"

        msg = (
            f"{emoji} *{tipo} aguardando sua resposta*\n\n"
            f"*Intencao:* {analise.intencao.value}\n"
            f"*Resumo:* {analise.resumo}\n\n"
            f"*Mensagem do comprador:*\n_{interacao.texto}_\n\n"
            f"*Sugestao do Claude ({resposta.confianca:.0%} confianca):*\n{resposta.texto}\n\n"
            f"Para responder, envie:\n`/r {interacao.id} sua resposta aqui`"
        )

        httpx.post(
            self._url,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
