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

    def escalar_mensagem(self, pack_id: str, nome_comprador: str, texto: str) -> None:
        """Notifica o humano sobre mensagem(ns) pos-venda de um comprador."""
        self._pendentes.adicionar(
            interacao_id=pack_id,
            texto=texto,
            intencao="mensagem_pos_venda",
            tipo="mensagem",
            nome_comprador=nome_comprador,
        )

        msg = (
            f"💬 Mensagem pos-venda\n"
            f"Comprador: {nome_comprador}\n\n"
            f"{texto}\n\n"
            f"/r {pack_id} sua resposta aqui"
        )

        self._enviar_telegram(msg)

    def _enviar_telegram(self, msg: str) -> None:
        if len(msg) > 4096:
            msg = msg[:4093] + "..."

        chat_id = config.TELEGRAM_CHAT_ID
        try:
            chat_id = int(chat_id)
        except (ValueError, TypeError):
            pass

        log.info(f"Enviando Telegram para chat_id={chat_id!r} (len={len(msg)})")
        resp = httpx.post(
            self._url,
            json={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
        if not resp.is_success:
            log.error(f"Telegram erro {resp.status_code}: {resp.text}")

    def escalar(self, interacao: Interacao, analise: Analise, resposta: Resposta) -> None:
        self._pendentes.adicionar(
            interacao_id=interacao.id,
            texto=interacao.texto,
            intencao=analise.intencao.value,
            tipo=interacao.tipo.value,
            nome_comprador=interacao.nome_comprador,
            titulo_item=interacao.titulo_item,
            sugestao=resposta.texto,
            confianca=resposta.confianca,
        )

        emoji = "🚨" if analise.urgente else "❓"
        # Converte MLB4342729373 -> MLB-4342729373 (formato da URL do produto)
        item_id_fmt = interacao.item_id.replace("MLB", "MLB-", 1) if interacao.item_id else ""
        item_link = f"https://produto.mercadolivre.com.br/{item_id_fmt}" if item_id_fmt else ""

        msg = (
            f"{emoji} {item_link}\n\n"
            f"Comprador: {interacao.texto}\n\n"
            f"/r {interacao.id} sua resposta aqui"
        )

        self._enviar_telegram(msg)
