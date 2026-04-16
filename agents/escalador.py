"""Escalador: notifica humano via Telegram quando o sistema nao sabe responder."""
import httpx

from config import config
from agents.monitor import Interacao
from agents.analisador import Analise
from agents.respondedor import Resposta


class Escalador:
    def __init__(self):
        self._url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    def escalar(self, interacao: Interacao, analise: Analise, resposta: Resposta) -> None:
        emoji = "🚨" if analise.urgente else "❓"
        tipo = "Pergunta" if interacao.tipo.value == "pergunta" else "Mensagem pos-venda"

        msg = (
            f"{emoji} *{tipo} sem resposta automatica*\n\n"
            f"*Intencao:* {analise.intencao.value}\n"
            f"*Resumo:* {analise.resumo}\n"
            f"*Confianca gerada:* {resposta.confianca:.0%}\n\n"
            f"*Mensagem do comprador:*\n_{interacao.texto}_\n\n"
            f"*Resposta sugerida (nao enviada):*\n{resposta.texto}\n\n"
            f"ID: `{interacao.id}`"
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
