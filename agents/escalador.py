"""Escalador: notifica humano via Telegram quando o sistema nao sabe responder."""
import logging
import httpx

from config import config
from agents.monitor import Interacao
from agents.analisador import Analise
from agents.respondedor import Resposta
from agents.pendentes import Pendentes

log = logging.getLogger(__name__)


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
            nome_comprador=interacao.nome_comprador,
        )

        emoji = "🚨" if analise.urgente else "❓"
        titulo = interacao.titulo_item or "sem titulo"

        msg = (
            f"{emoji} {titulo}\n\n"
            f"Comprador: {interacao.texto}\n\n"
            f"Sugestao ({resposta.confianca:.0%}): {resposta.texto}\n\n"
            f"/r {interacao.id} sua resposta aqui"
        )

        # Telegram limita mensagens a 4096 chars
        if len(msg) > 4096:
            rodape = f"\n\nPara responder:\n/r {interacao.id} sua resposta aqui"
            msg = msg[: 4096 - len(rodape)] + rodape

        # chat_id como int quando possivel (evita rejeicao por tipo incorreto)
        chat_id = config.TELEGRAM_CHAT_ID
        try:
            chat_id = int(chat_id)
        except (ValueError, TypeError):
            pass

        log.info(f"Enviando Telegram para chat_id={chat_id!r} (len={len(msg)})")
        resp = httpx.post(
            self._url,
            json={
                "chat_id": chat_id,
                "text": msg,
            },
            timeout=10,
        )
        if not resp.is_success:
            log.error(f"Telegram erro {resp.status_code}: {resp.text}")
