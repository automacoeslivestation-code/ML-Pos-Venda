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
            chat_id = msg.get("chat", {}).get("id")
            if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
                log.warning(f"Mensagem ignorada de chat_id nao autorizado: {chat_id}")
                continue
            texto = msg.get("text", "").strip()

            if texto.startswith("/r "):
                processadas += self._processar_resposta(texto)
            elif texto == "/listar":
                self._listar_pendentes()
            elif texto == "/status":
                self._status()
            elif texto.startswith("/cancelar "):
                self._cancelar(texto)
            elif texto == "/comandos":
                self._comandos()

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

    def _listar_pendentes(self) -> None:
        todos = self._pendentes.todos()
        if not todos:
            self._enviar_telegram("Nenhuma pergunta pendente.")
            return
        for iid, p in todos.items():
            tipo = p.get("tipo", "pergunta")
            texto = p.get("texto", "")
            if tipo == "mensagem":
                order_status = p.get("order_status", "")
                cabecalho = f"💬 Pós-venda" + (f" | {order_status}" if order_status else "")
            else:
                item_id = p.get("item_id", "")
                if item_id:
                    item_id_fmt = item_id.replace("MLB", "MLB-", 1)
                    link = f"https://produto.mercadolivre.com.br/{item_id_fmt}"
                    cabecalho = f"❓ Pergunta\n{link}"
                else:
                    cabecalho = "❓ Pergunta"
            msg = (
                f"{cabecalho}\n\n"
                f"Comprador: {texto}\n\n"
                f"/r {iid} sua resposta aqui"
            )
            self._enviar_telegram(msg)

    def _status(self) -> None:
        todos = self._pendentes.todos()
        total = len(todos)
        memoria = self._memoria.total()
        if total == 0:
            self._enviar_telegram(f"Tudo em dia! Nenhuma pendente.\nBase de conhecimento: {memoria} exemplos.")
        else:
            tipos = {"pergunta": 0, "mensagem": 0}
            for p in todos.values():
                tipos[p.get("tipo", "pergunta")] += 1
            self._enviar_telegram(
                f"Pendentes: {total}\n"
                f"  Perguntas: {tipos['pergunta']}\n"
                f"  Mensagens: {tipos['mensagem']}\n"
                f"Base de conhecimento: {memoria} exemplos.\n\n"
                f"Use /listar para ver detalhes."
            )

    def _cancelar(self, texto: str) -> None:
        """Remove uma pendente sem responder. Formato: /cancelar <id>"""
        partes = texto.split(" ", 1)
        if len(partes) < 2 or not partes[1].strip():
            self._enviar_telegram("Formato invalido. Use: /cancelar <id>")
            return
        interacao_id = partes[1].strip()
        pendente = self._pendentes.buscar(interacao_id)
        if not pendente:
            self._enviar_telegram(f"ID `{interacao_id}` nao encontrado ou ja respondido.")
            return
        self._pendentes.remover(interacao_id)
        self._enviar_telegram(f"Pendente `{interacao_id}` removido sem responder.")
        log.info(f"Pendente {interacao_id} cancelado pelo humano")

    def _comandos(self) -> None:
        msg = (
            "Comandos disponíveis:\n\n"
            "/r <id> <resposta>\n"
            "  Responde uma pergunta ou mensagem pendente no ML\n\n"
            "/listar\n"
            "  Mostra todas as perguntas/mensagens aguardando resposta\n\n"
            "/status\n"
            "  Resumo de pendentes e tamanho da base de conhecimento\n\n"
            "/cancelar <id>\n"
            "  Remove um pendente sem responder (ex: comprador ja resolveu)\n\n"
            "/comandos\n"
            "  Mostra esta lista"
        )
        self._enviar_telegram(msg)

    def _enviar_telegram(self, texto: str) -> None:
        try:
            httpx.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto},
                timeout=10,
            )
        except Exception as e:
            log.error(f"Erro ao enviar mensagem Telegram: {e}")
