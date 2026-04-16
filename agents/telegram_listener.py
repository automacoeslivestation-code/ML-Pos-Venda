"""TelegramListener: recebe respostas do humano via Telegram e processa."""
import logging
import httpx

from config import config
from agents.memoria import Memoria
from agents.pendentes import Pendentes
from agents.formatador import Formatador

log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


class TelegramListener:
    def __init__(self, ml_client):
        self._ml = ml_client
        self._memoria = Memoria()
        self._pendentes = Pendentes()
        self._formatador = Formatador()
        self._ultimo_update_id: int = 0

    def processar_respostas(self) -> int:
        """Verifica novas mensagens no Telegram e processa respostas do humano.
        Retorna o numero de respostas processadas.
        """
        updates = self._buscar_updates()
        processadas = 0

        for update in updates:
            self._ultimo_update_id = update["update_id"]
            msg = update.get("message", {})
            texto = msg.get("text", "").strip()

            if texto.startswith("/r "):
                processadas += self._processar_resposta(texto)

        return processadas

    def _buscar_updates(self) -> list[dict]:
        try:
            resp = httpx.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": self._ultimo_update_id + 1, "timeout": 5},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
        except Exception as e:
            log.error(f"Erro ao buscar updates do Telegram: {e}")
            return []

    def _processar_resposta(self, texto: str) -> int:
        """Formato esperado: /r <interacao_id> <resposta>"""
        partes = texto.split(" ", 2)
        if len(partes) < 3:
            log.warning(f"Formato invalido: {texto}")
            self._enviar_telegram("Formato invalido. Use: /r <id> <sua resposta>")
            return 0

        interacao_id = partes[1]
        resposta_bruta = partes[2].strip()

        pendente = self._pendentes.buscar(interacao_id)
        if not pendente:
            log.warning(f"Interacao {interacao_id} nao encontrada nos pendentes")
            self._enviar_telegram(f"ID `{interacao_id}` nao encontrado ou ja respondido.")
            return 0

        try:
            nome = pendente.get("nome_comprador", "")
            resposta_final = self._formatador.formatar(resposta_bruta, nome)

            self._postar_no_ml(interacao_id, pendente["tipo"], resposta_final)
            self._memoria.adicionar(pendente["texto"], resposta_final, pendente["intencao"])
            self._pendentes.remover(interacao_id)

            self._enviar_telegram(
                f"Postado no ML:\n\n_{resposta_final}_\n\n"
                f"Base atual: {self._memoria.total()} exemplos."
            )
            log.info(f"Resposta humana processada para {interacao_id}")
            return 1
        except Exception as e:
            log.error(f"Erro ao postar resposta para {interacao_id}: {e}")
            self._enviar_telegram(f"Erro ao postar resposta: {e}")
            return 0

    def _postar_no_ml(self, interacao_id: str, tipo: str, texto: str) -> None:
        if tipo == "pergunta":
            self._ml.responder_pergunta(interacao_id, texto)
        else:
            self._ml.responder_mensagem(interacao_id, texto)

    def _enviar_telegram(self, texto: str) -> None:
        try:
            httpx.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto},
                timeout=10,
            )
        except Exception as e:
            log.error(f"Erro ao enviar mensagem Telegram: {e}")
